# compel_compat.py — chunked SDXL prompt encoding without the compel library.
#
# Encodes prompts longer than 77 tokens by splitting into 75-token body chunks,
# each wrapped with BOS/EOS. Chunks are encoded independently and concatenated.
# Compatible with pipelines using enable_sequential_cpu_offload().

from app_debug import dlog as _dlog

_TAG = "compel_compat"
_CHUNK_BODY = 75  # tokens per chunk, excluding BOS and EOS


def _tokenize_full(tokenizer, text: str):
    """Tokenize without truncation and return a 1-D int tensor."""
    return tokenizer(text, truncation=False, return_tensors="pt").input_ids[0]


def dedup_tags(text: str) -> str:
    """Remove duplicate , ; . separated tags (case-insensitive), preserving first-occurrence order."""
    import re
    parts = re.split(r'\s*[,;.]\s*', text)
    seen: set = set()
    unique: list = []
    for part in parts:
        key = part.strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(part.strip())
    result = ', '.join(unique)
    if result != text:
        _dlog(_TAG, f"dedup_tags: removed {len(parts) - len(unique)} duplicate(s)")
    return result


# Words that carry no visual meaning for the image model.
_PROSE_STOP = frozenset({
    'a', 'an', 'the', 'and', 'or', 'but', 'so', 'yet',
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as',
    'into', 'through', 'about', 'between', 'around', 'near', 'over',
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'has', 'have', 'had', 'do', 'does', 'did',
    'she', 'he', 'it', 'her', 'his', 'its', 'they', 'their', 'them',
    'who', 'that', 'which', 'this', 'these', 'those',
    'tend', 'tends', 'reflects', 'combines', 'giving', 'give',
    'rather', 'than', 'often', 'also', 'more', 'most', 'very',
    # non-visual abstract nouns that survive basic stop-word filtering
    'features', 'silhouette', 'form', 'look', 'overall',
    'presence', 'movements',
})

_MAX_TAG_WORDS = 4  # cap per extracted phrase


def normalize_prompt(text: str) -> str:
    """Flatten mixed prose/tag prompts to compact tag format.

    Splits on sentence and clause boundaries, strips connector words,
    re-joins remaining words as short (≤4-word) tag phrases, then deduplicates.
    Safe to call on already-tag-style prompts — they pass through unchanged.
    """
    import re
    text = re.sub(r'[\n\r]+', ', ', text)
    fragments = re.split(r"(?<=[.!?])\s+|,\s*|;\s*", text)
    tags: list = []
    for frag in fragments:
        words = [w.strip(".,;:!?()'\"") for w in frag.split()]
        meaningful = [w for w in words
                      if w and w.lower() not in _PROSE_STOP and len(w) > 1]
        if not meaningful:
            continue
        tags.append(' '.join(meaningful[:_MAX_TAG_WORDS]))
    result = dedup_tags(', '.join(tags))
    if result != text.strip():
        _dlog(_TAG, f"normalize_prompt: {len(text)} chars → {len(result)} chars")
    return result


_delim_ids_cache: dict = {}


def _delim_ids(tokenizer) -> set:
    """Token ids for , ; . — cached per tokenizer type+vocab-size (stable across GC)."""
    key = (type(tokenizer).__name__, tokenizer.vocab_size)
    if key not in _delim_ids_cache:
        ids = set()
        for ch in (',', ';', '.'):
            ids.update(tokenizer(ch, add_special_tokens=False).input_ids)
        _delim_ids_cache[key] = ids
    return _delim_ids_cache[key]


def _split_chunks(tokenizer, text: str, device: str):
    """Split body tokens into ≤75-token pieces, preferring , ; . boundaries."""
    import torch
    ids = _tokenize_full(tokenizer, text)
    bos, eos = ids[:1], ids[-1:]
    body = ids[1:-1]
    pad_id = tokenizer.pad_token_id or 0
    delims = _delim_ids(tokenizer)

    chunks = []
    pos = 0
    while pos < max(len(body), 1):
        remaining = body[pos:]
        if len(remaining) <= _CHUNK_BODY:
            cut = len(remaining)
        else:
            # scan backwards for last delimiter within the window
            cut = _CHUNK_BODY
            for i in range(_CHUNK_BODY - 1, -1, -1):
                if remaining[i].item() in delims:
                    cut = i + 1  # include the delimiter token
                    break
        piece = remaining[:cut]
        needed = _CHUNK_BODY - len(piece)
        padded = torch.cat([bos, piece, eos,
                            torch.full((needed,), pad_id, dtype=torch.long)])
        chunks.append(padded.unsqueeze(0).to(device))
        chunk_text = tokenizer.decode(piece, skip_special_tokens=True)
        _dlog(_TAG, f"  chunk {len(chunks)}: {len(piece)} tokens | {chunk_text!r}")
        pos += cut
    _dlog(_TAG, f"_split_chunks: {len(chunks)} chunk(s) for {len(ids)} tokens")
    return chunks


def _pad_to(chunk_list: list, n_target: int, tokenizer, device: str) -> list:
    """Return a new list extended to n_target entries with zero-body padding chunks."""
    import torch
    if len(chunk_list) >= n_target:
        return list(chunk_list)
    pad_id = tokenizer.pad_token_id or 0
    bos_id = tokenizer.bos_token_id or chunk_list[0][0, 0].item()
    eos_id = tokenizer.eos_token_id or tokenizer.sep_token_id or 0
    bos = torch.tensor([bos_id], dtype=torch.long, device=device)
    eos = torch.tensor([eos_id], dtype=torch.long, device=device)
    pad_body = torch.full((_CHUNK_BODY,), pad_id, dtype=torch.long, device=device)
    zero_chunk = torch.cat([bos, pad_body, eos]).unsqueeze(0)
    result = list(chunk_list)
    while len(result) < n_target:
        result.append(zero_chunk)
    return result


def _encode_te(text_encoder, chunks: list):
    """Encode a list of [1,77] chunks; returns penultimate hidden states catted on dim 1."""
    import torch
    parts = []
    with torch.no_grad():
        for ids in chunks:
            out = text_encoder(ids, output_hidden_states=True, return_dict=True)
            parts.append(out.hidden_states[-2])
    return torch.cat(parts, dim=1)


def _encode_te2_with_pooled(text_encoder_2, chunks: list):
    """OpenCLIP variant: returns (hidden_states, pooled) where pooled comes from chunk 0."""
    import torch
    parts = []
    pooled = None
    with torch.no_grad():
        for i, ids in enumerate(chunks):
            out = text_encoder_2(ids, output_hidden_states=True, return_dict=True)
            parts.append(out.hidden_states[-2])
            if i == 0:
                pooled = out.text_embeds
    return torch.cat(parts, dim=1), pooled


def encode_prompt_sdxl_chunked(pipe, prompt: str, negative_prompt: str, device: str):
    """Encode an SDXL prompt/negative pair with full long-prompt support.

    Splits each text into 75-token body chunks, encodes via pipe.text_encoder and
    pipe.text_encoder_2 (sequential-offload-compatible), then concatenates.

    Returns:
        (prompt_embeds, neg_embeds, pooled_prompt_embeds, neg_pooled_embeds)
        All tensors are on *device*.
    """
    _dlog(_TAG, f"encode prompt ({len(prompt)} chars): {prompt!r}")
    _dlog(_TAG, f"encode negative ({len(negative_prompt)} chars): {negative_prompt!r}")
    prompt          = normalize_prompt(prompt)
    negative_prompt = normalize_prompt(negative_prompt)

    pos_c1 = _split_chunks(pipe.tokenizer,   prompt,           device)
    neg_c1 = _split_chunks(pipe.tokenizer,   negative_prompt,  device)
    pos_c2 = _split_chunks(pipe.tokenizer_2, prompt,           device)
    neg_c2 = _split_chunks(pipe.tokenizer_2, negative_prompt,  device)

    # All four lists must share one chunk count so te1/te2 token-seq lengths match.
    n = max(len(pos_c1), len(neg_c1), len(pos_c2), len(neg_c2))
    pos_c1 = _pad_to(pos_c1, n, pipe.tokenizer,   device)
    neg_c1 = _pad_to(neg_c1, n, pipe.tokenizer,   device)
    pos_c2 = _pad_to(pos_c2, n, pipe.tokenizer_2, device)
    neg_c2 = _pad_to(neg_c2, n, pipe.tokenizer_2, device)
    _dlog(_TAG, f"chunk count n={n}")

    pos_te1 = _encode_te(pipe.text_encoder, pos_c1)
    neg_te1 = _encode_te(pipe.text_encoder, neg_c1)
    pos_te2, pooled_pos = _encode_te2_with_pooled(pipe.text_encoder_2, pos_c2)
    neg_te2, pooled_neg = _encode_te2_with_pooled(pipe.text_encoder_2, neg_c2)

    import torch
    # SDXL cross-attention expects CLIP ‖ OpenCLIP concatenated on the feature axis.
    prompt_embeds = torch.cat([pos_te1, pos_te2], dim=-1)
    neg_embeds    = torch.cat([neg_te1, neg_te2], dim=-1)

    _dlog(_TAG, f"prompt_embeds shape={prompt_embeds.shape} device={prompt_embeds.device}")
    _dlog(_TAG, f"neg_embeds    shape={neg_embeds.shape}    device={neg_embeds.device}")
    return prompt_embeds, neg_embeds, pooled_pos, pooled_neg
