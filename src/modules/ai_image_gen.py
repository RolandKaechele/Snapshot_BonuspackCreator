"""AI Image Generator — Perchance.org txt2img integration.

Opens a prompt dialog from Pictures, Love Lens, and Events widgets;
generates images via the perchance.org AI image service; then shows a
selection picker so the user can choose which images to keep.
"""

import http.client
import http.cookiejar
import json
import os
import random
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QSlider, QListWidget, QListWidgetItem,
    QSplitter, QWidget, QGroupBox, QFormLayout,
    QDialogButtonBox, QProgressBar, QStackedWidget,
)

from app_debug import dlog as _dlog, is_debug as _is_debug
from ui.dialogs import show_error

# ─── Type / prompt-enhancement dictionaries per widget ───────────────────────

PHOTO_TYPES: dict[str, dict] = {
    "upskirt": {
        "label": "Upskirt Shot",
        "prompt_enhancement": (
            "nsfw, "
            "low angle upskirt shot, panties clearly visible, "
            "short pleated skirt, anime style, high quality"
        ),
    },
    "jogger": {
        "label": "Jogger Photo",
        "prompt_enhancement": (
            "nsfw, "
            "jogging pose, sports bra, spandex shorts, dynamic running motion, "
            "anime style, high quality"
        ),
    },
    "xray": {
        "label": "X-Ray Upskirt",
        "prompt_enhancement": (
            "nsfw, "
            "x-ray vision style, see-through skirt, panties visible, "
            "anime style, high quality"
        ),
    },
    "bench": {
        "label": "Bench Photo",
        "prompt_enhancement": (
            "nsfw, "
            "sitting on park bench, legs together, short skirt, "
            "anime style, high quality"
        ),
    },
    "bar": {
        "label": "Bar Photo (Barstool)",
        "prompt_enhancement": (
            "nsfw, "
            "sitting on barstool at bar counter, cocktail dress, "
            "anime style, high quality"
        ),
    },
    "photoBooth": {
        "label": "Photo Booth",
        "prompt_enhancement": (
            "nsfw, "
            "inside photo booth, striped curtain background, cute pose, "
            "anime style, high quality"
        ),
    },
    "event": {
        "label": "City Event Photo",
        "prompt_enhancement": (
            "nsfw, "
            "outdoor city event, crowd in background, casual clothing, "
            "anime style, high quality"
        ),
    },
    "hypno": {
        "label": "Love Lens / Hypno Photo",
        "prompt_enhancement": (
            "nsfw, "
            "hypnotic spiral eyes, dazed blissful expression, standing pose, "
            "anime style, high quality"
        ),
    },
    "police": {
        "label": "Police Upskirt",
        "prompt_enhancement": (
            "nsfw, "
            "female police officer uniform, skirt, upskirt angle, "
            "anime style, high quality"
        ),
    },
    "flasher": {
        "label": "Flasher (Yoruko Task)",
        "prompt_enhancement": (
            "nsfw, "
            "opening coat to flash, mischievous smile, trench coat, "
            "anime style, high quality"
            "naked body, exposed breasts, exposed genitals"
        ),
    },
    "window": {
        "label": "Window (Yoruko Task)",
        "prompt_enhancement": (
            "nsfw, "
            "standing at open window, "
            "anime style, high quality"
            "naked body, exposed breasts, exposed genitals"
            "caught in the act, surprised expression, looking outside, "
            "sex tools"
        ),
    },
}

LOVE_LENS_TYPES: dict[str, dict] = {
    "standing_topless": {
        "label": "Standing Topless",
        "prompt_enhancement": (
            "nsfw, "
            "standing upright, topless, bare chest, confident pose, "
            "full body, anime style, high quality"
        ),
    },
    "standing_nude": {
        "label": "Standing Nude",
        "prompt_enhancement": (
            "nsfw, "
            "standing upright, fully nude, tasteful pose, "
            "full body, anime style, high quality"
        ),
    },
    "kneeling_cum_mouth": {
        "label": "Kneeling – Cum in Mouth",
        "prompt_enhancement": (
            "nsfw, "
            "kneeling pose, mouth open, ahegao expression, cum in mouth, "
            "anime style, high quality"
        ),
    },
    "kneeling_cum_face": {
        "label": "Kneeling – Cum on Face",
        "prompt_enhancement": (
            "nsfw, "
            "kneeling pose, cum on face, satisfied expression, "
            "anime style, high quality"
        ),
    },
    "leaning_cum_butt": {
        "label": "Leaning – Cum on Butt",
        "prompt_enhancement": (
            "nsfw, "
            "leaning forward, cum dripping on buttocks, rear view, "
            "anime style, high quality"
        ),
    },
    "leaning_cum_vagina": {
        "label": "Leaning – Cum in Vagina",
        "prompt_enhancement": (
            "nsfw, "
            "leaning forward pose, cum dripping from vagina, rear view, "
            "anime style, high quality"
        ),
    },
    "leaning_cum_anus": {
        "label": "Leaning – Cum in Anus",
        "prompt_enhancement": (
            "nsfw, "
            "leaning forward pose, cum dripping from anus, rear view, "
            "anime style, high quality"
        ),
    },
}

EVENT_TYPES: dict[str, dict] = {
    "alley_night": {
        "label": "Dark Alley – Night",
        "prompt_enhancement": (
            "nsfw, "
            "dark alley, night-time, neon signs reflected on wet pavement, "
            "cyberpunk atmosphere, anime background, no characters, high quality"
        ),
    },
    "city_street_day": {
        "label": "City Street – Day",
        "prompt_enhancement": (
            "nsfw, "
            "busy city street, daytime, shop-lined sidewalk, pedestrians, "
            "anime background, no characters in foreground, high quality"
        ),
    },
    "park_day": {
        "label": "Park – Day",
        "prompt_enhancement": (
            "nsfw, "
            "city park, sunny day, trees, park benches, birds, "
            "anime background, no characters, high quality"
        ),
    },
    "school_grounds": {
        "label": "School Grounds",
        "prompt_enhancement": (
            "nsfw, "
            "schoolyard, outside school building, sakura trees, "
            "anime background, no characters, high quality"
        ),
    },
    "bar_interior": {
        "label": "Bar Interior",
        "prompt_enhancement": (
            "nsfw, "
            "bar interior, dim lighting, neon signs, bottles on shelves, "
            "bar counter, anime background, no characters, high quality"
        ),
    },
    "office_interior": {
        "label": "Office Interior",
        "prompt_enhancement": (
            "nsfw, "
            "office interior, desks, computer monitors, city view window, "
            "anime background, no characters, high quality"
        ),
    },
    "beach_daytime": {
        "label": "Beach – Daytime",
        "prompt_enhancement": (
            "nsfw, "
            "beach, ocean waves, white sand, palm trees, sunny sky, "
            "anime background, no characters, high quality"
        ),
    },
    "rooftop_night": {
        "label": "Rooftop – Night",
        "prompt_enhancement": (
            "nsfw, "
            "city rooftop, night-time, glittering skyline, starry sky, "
            "anime background, no characters, high quality"
        ),
    },
}

LOVE_LENS_OVERLAY_TYPES: dict[str, dict] = {
    "overlayStart": {
        "label": "Overlay – Start",
        "prompt_enhancement": (
            "nsfw, "
            "standing, hypnotic dazed expression, arms relaxed, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayBoob": {
        "label": "Overlay – Grabbing Breasts",
        "prompt_enhancement": (
            "nsfw, "
            "topless, hands cupping own breasts, ahegao expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayPussy": {
        "label": "Overlay – Grabbing Vagina",
        "prompt_enhancement": (
            "nsfw, "
            "nude, hand between legs touching vagina, blissful expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayButt": {
        "label": "Overlay – Grabbing Butt",
        "prompt_enhancement": (
            "nsfw, "
            "nude, hands on own buttocks, ahegao expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
    "overlayVaginalStart": {
        "label": "Overlay – Vaginal Start",
        "prompt_enhancement": (
            "nsfw, "
            "nude, legs slightly apart, anticipating blissful expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayVaginalPenetration": {
        "label": "Overlay – Vaginal Penetration",
        "prompt_enhancement": (
            "nsfw, "
            "nude, vaginal penetration pose, ahegao expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayVaginalCum": {
        "label": "Overlay – Vaginal Cum",
        "prompt_enhancement": (
            "nsfw, "
            "nude, cum dripping from vagina, satisfied ahegao expression, "
            "full body front view, anime style, high quality, transparent background"
        ),
    },
    "overlayAnalStart": {
        "label": "Overlay – Anal Start",
        "prompt_enhancement": (
            "nsfw, "
            "nude, bent forward slightly, anticipating expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
    "overlayAnalPenetration": {
        "label": "Overlay – Anal Penetration",
        "prompt_enhancement": (
            "nsfw, "
            "nude, anal penetration pose, ahegao expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
    "overlayAnalCum": {
        "label": "Overlay – Anal Cum",
        "prompt_enhancement": (
            "nsfw, "
            "nude, cum dripping from anus, satisfied ahegao expression, "
            "full body rear view, anime style, high quality, transparent background"
        ),
    },
}

LEWD_SHORES_PHOTO_TYPES: dict[str, dict] = {
    "beachFront": {
        "label": "Beach – Front",
        "prompt_enhancement": (
            "nsfw, "
            "standing on beach, ocean background, bikini or swimsuit, "
            "front view, anime style, high quality"
        ),
    },
    "beachBack": {
        "label": "Beach – Back",
        "prompt_enhancement": (
            "nsfw, "
            "standing on beach, ocean background, bikini or swimsuit, "
            "rear view, anime style, high quality"
        ),
    },
    "exposedFront": {
        "label": "Exposed – Front",
        "prompt_enhancement": (
            "nsfw, "
            "outdoor beach setting, topless or nude, "
            "front view, anime style, high quality"
        ),
    },
    "exposedBack": {
        "label": "Exposed – Back",
        "prompt_enhancement": (
            "nsfw, "
            "outdoor beach setting, topless or nude, "
            "rear view, anime style, high quality"
        ),
    },
    "yoga": {
        "label": "Yoga",
        "prompt_enhancement": (
            "nsfw, "
            "yoga pose, sports bra, yoga pants, "
            "anime style, high quality"
        ),
    },
    "shower": {
        "label": "Shower",
        "prompt_enhancement": (
            "nsfw, "
            "standing in shower, wet body, water droplets, "
            "anime style, high quality, "
            "sex"
        ),
    },
    "wc": {
        "label": "WC",
        "prompt_enhancement": (
            "nsfw, "
            "sitting on toilet, bathroom setting, panties around ankles, "
            "anime style, high quality, "
            "peeing, urination"
        ),
    },
    "mermaid": {
        "label": "Mermaid (Lying on Stomach)",
        "prompt_enhancement": (
            "nsfw, "
            "lying on stomach on beach sand, mermaid pose, "
            "bikini or topless, rear view, anime style, high quality"
        ),
    },
    "underwater": {
        "label": "Underwater",
        "prompt_enhancement": (
            "nsfw, "
            "underwater scene, swimming, bubbles, bikini, "
            "anime style, high quality, "
            "sex"
        ),
    },
    "police": {
        "label": "Lifeguard",
        "prompt_enhancement": (
            "nsfw, "
            "lifeguard uniform, standing on beach, confident pose, "
            "anime style, high quality"
        ),
    },
    "sPolice": {
        "label": "Sitting Lifeguard",
        "prompt_enhancement": (
            "nsfw, "
            "lifeguard uniform, sitting on lifeguard tower, relaxed pose, "
            "anime style, high quality"
        ),
    },
    "booth": {
        "label": "Booth",
        "prompt_enhancement": (
            "nsfw, "
            "inside changing booth, undressing, swimsuit, "
            "anime style, high quality"
        ),
    },
    "angry": {
        "label": "Busted",
        "prompt_enhancement": (
            "nsfw, "
            "caught in the act, surprised or embarrassed expression, "
            "anime style, high quality"
        ),
    },
}

SNAPSHOT_PHOTO_MODIFIERS: dict[str, dict] = {
    "plain": {
        "label": "Plain",
        "prompt_enhancement": "plain cotton panties",
    },
    "stripes": {
        "label": "Stripes",
        "prompt_enhancement": "striped panties",
    },
    "dots": {
        "label": "Dots",
        "prompt_enhancement": "polka dot panties",
    },
    "frill": {
        "label": "Frill",
        "prompt_enhancement": "frilly lace panties",
    },
    "kinky": {
        "label": "Kinky",
        "prompt_enhancement": "kinky harness straps, erotic underwear",
    },
    "none": {
        "label": "None (no underwear)",
        "prompt_enhancement": "no underwear, bare skin",
    },
    "plug": {
        "label": "Plug",
        "prompt_enhancement": "butt plug visible",
    },
    "piercing": {
        "label": "Piercing",
        "prompt_enhancement": "genital piercing visible",
    },
    "cum": {
        "label": "Cum",
        "prompt_enhancement": "cum on panties",
    },
    "nude": {
        "label": "Nude",
        "prompt_enhancement": "fully nude, no clothing",
    },
    "flashing": {
        "label": "Flashing",
        "prompt_enhancement": "flashing, lifting skirt, exposing self",
    },
    "sex": {
        "label": "Sex",
        "prompt_enhancement": "nsfw explicit, sexual intercourse",
    },
    "topless": {
        "label": "Topless",
        "prompt_enhancement": "topless, bare breasts exposed",
    },
    "dildo": {
        "label": "Dildo",
        "prompt_enhancement": "using a dildo",
    },
    "mastubrate": {
        "label": "Masturbate",
        "prompt_enhancement": "masturbating, hand between legs",
    },
    "front": {
        "label": "Front view",
        "prompt_enhancement": "front view",
    },
    "back": {
        "label": "Back view",
        "prompt_enhancement": "rear view, back to camera",
    },
    "goth": {
        "label": "Goth",
        "prompt_enhancement": "gothic style, black lace lingerie, dark aesthetic",
    },
}

LEWD_SHORES_PHOTO_MODIFIERS: dict[str, dict] = {
    "front view": {
        "label": "Front View",
        "prompt_enhancement": "facing camera, front view",
    },
    "back view": {
        "label": "Back View",
        "prompt_enhancement": "back to camera, rear view",
    },
    "butt view": {
        "label": "Butt View",
        "prompt_enhancement": "buttocks facing camera, rear view",
    },
    "changing": {
        "label": "Changing",
        "prompt_enhancement": "mid-change, removing swimsuit",
    },
    "cameltoe": {
        "label": "Cameltoe",
        "prompt_enhancement": "cameltoe visible through tight swimsuit",
    },
    "flashing": {
        "label": "Flashing",
        "prompt_enhancement": "flashing, pulling aside swimsuit",
    },
    "yoga": {
        "label": "Yoga Pose",
        "prompt_enhancement": "yoga pose, flexible stretch",
    },
    "mermaid": {
        "label": "Mermaid (Lying)",
        "prompt_enhancement": "lying on stomach, mermaid pose",
    },
    "booth": {
        "label": "Booth",
        "prompt_enhancement": "inside changing booth, curtain visible",
    },
    "none": {
        "label": "None",
        "prompt_enhancement": "",
    },
}

PHOTO_MODIFIER_TYPES: dict[str, dict[str, dict]] = {
    "photos": SNAPSHOT_PHOTO_MODIFIERS,
    "photos_lewdshores": LEWD_SHORES_PHOTO_MODIFIERS,
}

WIDGET_TYPES: dict[str, dict[str, dict]] = {
    "photos": PHOTO_TYPES,
    "photos_lewdshores": LEWD_SHORES_PHOTO_TYPES,
    "love_lens": LOVE_LENS_TYPES,
    "love_lens_overlays": LOVE_LENS_OVERLAY_TYPES,
    "events": EVENT_TYPES,
}

# ─── Perchance API helpers ────────────────────────────────────────────────────

_PERCHANCE_PAGE_URL   = "https://perchance.org/ai-anime-generator"
_PERCHANCE_ACCESS_URL = "https://perchance.org/api/getAccessCodeForAdPoweredStuff"
_IMGGEN_EMBED_URL     = "https://image-generation.perchance.org/embed"
_IMGGEN_VERIFY_URL    = "https://image-generation.perchance.org/api/verifyUser"
_PERCHANCE_GEN_URL    = "https://image-generation.perchance.org/api/generate"
_IMGGEN_DOWNLOAD_URL  = "https://image-generation.perchance.org"

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_BASE_HEADERS = {
    "User-Agent": _UA,
    "Accept": "application/json, text/plain, */*",
}
_IMGGEN_HEADERS = {
    **_BASE_HEADERS,
    "Origin": "https://image-generation.perchance.org",
    "Referer": "https://image-generation.perchance.org/embed",
}

# Shared cookie-aware opener — established once per worker run so the
# access-code fetch and generate request share the same browser session.
def _make_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [("User-Agent", _UA)]
    return opener


def _debug_dump(name: str, content: bytes, ext: str = "html") -> None:
    if not _is_debug():
        return
    tmp_dir = os.path.join(tempfile.gettempdir(), "snapshot_pack_creator_ai")
    os.makedirs(tmp_dir, exist_ok=True)
    path = os.path.join(tmp_dir, f"debug_{name}_{int(time.time())}.{ext}")
    with open(path, "wb") as fh:
        fh.write(content)
    _dlog("ai_image_gen._debug_dump", f"saved {path}")


def _get_session(opener: urllib.request.OpenerDirector) -> tuple[str, str]:
    """Return (ad_access_code, user_key) by running the Perchance auth flow.

    1. Visit the embed page to establish the image-generation.perchance.org context.
    2. Call /api/verifyUser to obtain a userKey.
    3. Fetch the time-keyed adAccessCode from perchance.org.
    """
    # 1. Seed the embed context (not strictly needed for cookies, but mirrors the browser).
    embed_req = urllib.request.Request(
        _IMGGEN_EMBED_URL,
        headers={**_IMGGEN_HEADERS, "Accept": "text/html,application/xhtml+xml,*/*"},
    )
    with opener.open(embed_req, timeout=15) as resp:
        _debug_dump("embed_seed", resp.read(4096), "html")

    # 2. Obtain userKey — /api/verifyUser returns {status, userKey} immediately.
    verify_url = f"{_IMGGEN_VERIFY_URL}?thread=0&__cacheBust={random.random()}"
    verify_req = urllib.request.Request(verify_url, headers=_IMGGEN_HEADERS)
    with opener.open(verify_req, timeout=20) as resp:
        verify_raw = resp.read()
    verify_data = json.loads(verify_raw)
    _debug_dump("verify_user", verify_raw, "json")
    user_key = verify_data.get("userKey", "")
    _dlog("ai_image_gen._get_session", f"verifyUser status={verify_data.get('status')!r} userKey={user_key[:10]}…")
    if not user_key:
        raise RuntimeError(f"perchance.org verifyUser failed: {verify_data.get('status')!r}")

    # 3. Fetch the time-keyed adAccessCode (refreshes every 10 minutes).
    cache_bust = round(time.time() / 600)
    access_url = f"{_PERCHANCE_ACCESS_URL}?__cacheBust={cache_bust}"
    access_req = urllib.request.Request(access_url, headers=_BASE_HEADERS)
    with opener.open(access_req, timeout=15) as resp:
        access_raw = resp.read()
    ad_access_code = access_raw.decode().strip()
    _debug_dump("access_code", access_raw, "txt")
    _dlog("ai_image_gen._get_session", f"adAccessCode={ad_access_code[:10]}…")
    if not ad_access_code:
        raise RuntimeError("perchance.org returned empty adAccessCode")

    return ad_access_code, user_key


def _request_generate(prompt: str, ad_access_code: str, user_key: str,
                      opener: urllib.request.OpenerDirector) -> dict:
    """POST one generation request; return the parsed response dict."""
    request_id = str(random.random())
    params = urllib.parse.urlencode({
        "userKey": user_key,
        "requestId": request_id,
        "adAccessCode": ad_access_code,
        "__cacheBust": str(random.random()),
    })
    body = json.dumps({
        "prompt": prompt,
        "negativePrompt": "ugly, bad anatomy, blurry, low quality, watermark, text, logo",
        "seed": str(random.randint(0, 2**31)),
        "resolution": "512x512",
        "guidanceScale": "7",
        "channel": "ai-anime-generator",
        "subChannel": "public",
        "userKey": user_key,
        "adAccessCode": ad_access_code,
        "requestId": request_id,
    }).encode()
    headers = {**_IMGGEN_HEADERS, "Content-Type": "application/json"}
    req = urllib.request.Request(f"{_PERCHANCE_GEN_URL}?{params}", data=body, headers=headers)
    with opener.open(req, timeout=120) as resp:
        raw = resp.read()
    _debug_dump("generate_response", raw, "json")
    parsed = json.loads(raw)
    status = parsed.get("status", "")
    _dlog("ai_image_gen._request_generate", f"status={status!r} keys={list(parsed.keys())}")
    if status != "success":
        raise RuntimeError(f"perchance.org generate error: {status}")
    return parsed


def _download_bytes(url: str, opener: urllib.request.OpenerDirector,
                    retries: int = 4) -> bytes:
    # Relative URLs come from the image-generation subdomain.
    if url.startswith("/"):
        url = f"{_IMGGEN_DOWNLOAD_URL}{url}"
    req = urllib.request.Request(url, headers=_IMGGEN_HEADERS)
    last_exc: Exception = RuntimeError("download failed")
    for attempt in range(retries):
        try:
            with opener.open(req, timeout=60) as resp:
                return resp.read()
        except (http.client.IncompleteRead, TimeoutError, ConnectionResetError) as exc:
            last_exc = exc
            _dlog("ai_image_gen._download_bytes",
                  f"attempt {attempt + 1}/{retries} failed: {exc}")
            time.sleep(2 ** attempt)  # 1 s, 2 s, 4 s back-off
    raise last_exc


def _save_to_temp(image_bytes: bytes, idx: int, ext: str = "jpeg",
                  output_dir: str | None = None) -> str:
    if output_dir:
        dest = output_dir
    else:
        dest = os.path.join(tempfile.gettempdir(), "snapshot_pack_creator_ai")
    os.makedirs(dest, exist_ok=True)
    filename = f"{int(time.time())}_{idx}.{ext}"
    path = os.path.join(dest, filename)
    with open(path, "wb") as fh:
        fh.write(image_bytes)
    return path


# ─── Background worker ────────────────────────────────────────────────────────

class _GenerationWorker(QThread):
    """Calls the perchance API in a background thread."""

    progress = pyqtSignal(str)
    image_ready = pyqtSignal(str, str, str)  # (path, pos_key, mod_key)
    finished = pyqtSignal(list)              # list[tuple[str, str, str]]
    error = pyqtSignal(str)

    def __init__(self, prompts: list[tuple[str, str, str]], n_per_prompt: int,
                 output_dir: str | None = None) -> None:
        super().__init__()
        self._prompts = prompts  # [(prompt_text, pos_key, mod_key), ...]
        self._n = n_per_prompt
        self._output_dir = output_dir
        self._abort = False

    def abort(self) -> None:
        self._abort = True

    def run(self) -> None:
        try:
            opener = _make_opener()
            self.progress.emit("Establishing session with perchance.org…")
            ad_access_code, user_key = _get_session(opener)
            pairs: list[tuple[str, str, str]] = []  # (path, pos_key, mod_key)
            total = len(self._prompts)
            for pi, (prompt, pos_key, mod_key) in enumerate(self._prompts):
                for ji in range(self._n):
                    if self._abort:
                        break
                    self.progress.emit(
                        f"Generating image {ji + 1}/{self._n} "
                        f"(prompt {pi + 1}/{total})…"
                    )
                    # Refresh session on invalid_key; retry once.
                    for attempt in range(2):
                        try:
                            result = _request_generate(
                                prompt, ad_access_code, user_key, opener
                            )
                            break
                        except RuntimeError as exc:
                            if "invalid_key" in str(exc) and attempt == 0:
                                self.progress.emit(
                                    f"Session expired – refreshing "
                                    f"(prompt {pi + 1}/{total})…"
                                )
                                ad_access_code, user_key = _get_session(opener)
                            else:
                                raise
                    dl_url = result.get("imageDownloadUrl") or result.get("imageId", "")
                    if not dl_url:
                        _dlog("_GenerationWorker.run", f"no download URL in result: {result}")
                        continue
                    self.progress.emit(
                        f"Downloading image {ji + 1}/{self._n} "
                        f"(prompt {pi + 1}/{total})…"
                    )
                    data = _download_bytes(dl_url, opener)
                    ext = result.get("fileExtension", "jpeg")
                    path = _save_to_temp(data, len(pairs), ext, self._output_dir)
                    pairs.append((path, pos_key, mod_key))
                    self.image_ready.emit(path, pos_key, mod_key)
                    time.sleep(1.5)  # avoid rate-limiting between requests
                if self._abort:
                    break
            self.finished.emit(pairs)
        except Exception as exc:
            _dlog("_GenerationWorker.run", f"error: {exc}")
            self.error.emit(str(exc))


# ─── Image Picker Dialog ──────────────────────────────────────────────────────

class ImagePickerDialog(QDialog):
    """Shows generated images; user selects which to keep."""

    def __init__(
        self,
        parent: QWidget,
        paths: list[str],
        on_accepted: Callable[[dict], None],
        type_map: dict[str, tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Select AI-Generated Images")
        self.resize(860, 560)
        self._paths = list(paths)
        self._on_accepted = on_accepted
        self._type_map: dict[str, tuple[str, str]] = type_map or {}
        self._build_ui()
        self._populate(paths)

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        root.addWidget(QLabel("Select the images to add to the pack:"))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # Thumbnail list
        self._list = QListWidget()
        self._list.setViewMode(QListWidget.ViewMode.IconMode)
        self._list.setIconSize(QSize(120, 120))
        self._list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection
        )
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._list)

        # Large preview
        self._preview = QLabel("Select an image to preview")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumWidth(320)
        splitter.addWidget(self._preview)
        splitter.setSizes([420, 400])

        # Select-all / deselect-all helpers
        sel_row = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_all.setFixedWidth(90)
        btn_none.setFixedWidth(90)
        btn_all.clicked.connect(self._list.selectAll)
        btn_none.clicked.connect(self._list.clearSelection)
        sel_row.addWidget(btn_all)
        sel_row.addWidget(btn_none)
        sel_row.addStretch()
        self._lbl_count = QLabel("0 selected")
        sel_row.addWidget(self._lbl_count)
        root.addLayout(sel_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate(self, paths: list[str]) -> None:
        for path in paths:
            self._add_item(path)

    def add_path(self, path: str) -> None:
        """Called live when the worker delivers an extra image."""
        self._paths.append(path)
        self._add_item(path)

    def _add_item(self, path: str) -> None:
        px = QPixmap(path)
        item = QListWidgetItem(os.path.basename(path))
        if not px.isNull():
            from PyQt6.QtGui import QIcon
            item.setIcon(QIcon(px.scaled(
                120, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )))
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setSelected(True)
        self._list.addItem(item)
        self._update_count()

    def _on_selection_changed(self) -> None:
        self._update_count()
        selected = self._list.selectedItems()
        if not selected:
            self._preview.setPixmap(QPixmap())
            self._preview.setText("Select an image to preview")
            return
        path = selected[-1].data(Qt.ItemDataRole.UserRole)
        px = QPixmap(path)
        if px.isNull():
            self._preview.setText("Cannot preview")
            return
        w = max(self._preview.width(), 300)
        h = max(self._preview.height(), 300)
        self._preview.setPixmap(
            px.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _update_count(self) -> None:
        n = len(self._list.selectedItems())
        self._lbl_count.setText(f"{n} selected")

    def _on_ok(self) -> None:
        selected_paths = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._list.selectedItems()
        ]
        self.accept()
        if selected_paths:
            self._on_accepted({p: self._type_map.get(p, ("", "")) for p in selected_paths})


# ─── Main AI Generate Dialog ──────────────────────────────────────────────────

class AiImageGenDialog(QDialog):
    """
    Prompt editor + generate trigger for the perchance.org txt2img service.

    widget_type  : "photos" | "love_lens" | "events"
    on_accepted  : called with list[str] of selected temp-file paths
    """

    def __init__(
        self,
        parent: QWidget,
        widget_type: str,
        on_accepted: Callable[[dict], None],
        output_dir: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Image Generator – perchance.org")
        self.resize(680, 540)
        self._widget_type = widget_type
        self._type_map: dict[str, dict] = WIDGET_TYPES.get(widget_type, {})
        self._modifier_map: dict[str, dict] = PHOTO_MODIFIER_TYPES.get(widget_type, {})
        self._on_accepted = on_accepted
        self._output_dir = output_dir
        self._worker: _GenerationWorker | None = None
        self._picker: ImagePickerDialog | None = None
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_form_page())   # 0
        self._stack.addWidget(self._build_progress_page())  # 1
        self._stack.setCurrentIndex(0)

    def _build_form_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── Type selector ─────────────────────────────────────────────────
        type_group = QGroupBox("Image Type")
        type_form = QFormLayout(type_group)
        self._cmb_type = QComboBox()
        for key, info in self._type_map.items():
            self._cmb_type.addItem(info["label"], key)
        self._cmb_type.currentIndexChanged.connect(self._on_type_changed)
        type_form.addRow("Position:", self._cmb_type)
        if self._modifier_map:
            self._cmb_modifier = QComboBox()
            self._cmb_modifier.addItem("(any)", "")
            for key, info in self._modifier_map.items():
                self._cmb_modifier.addItem(info["label"], key)
            type_form.addRow("Photo Type:", self._cmb_modifier)
        else:
            self._cmb_modifier = None
        layout.addWidget(type_group)

        # ── Base prompt ───────────────────────────────────────────────────
        prompt_group = QGroupBox("Base Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        self._edit_prompt = QTextEdit()
        self._edit_prompt.setPlaceholderText(
            "Describe the subject/character, e.g. "
            '"anime girl, black hair, school uniform"'
        )
        self._edit_prompt.setFixedHeight(70)
        prompt_layout.addWidget(self._edit_prompt)
        layout.addWidget(prompt_group)

        # ── Prompt enhancement ────────────────────────────────────────────
        enh_group = QGroupBox("Prompt Enhancement  (pre-filled by type; expand freely)")
        enh_layout = QVBoxLayout(enh_group)
        self._edit_enhancement = QTextEdit()
        self._edit_enhancement.setFixedHeight(90)
        enh_layout.addWidget(self._edit_enhancement)
        layout.addWidget(enh_group)

        # ── Image count slider ────────────────────────────────────────────
        count_group = QGroupBox("Number of Images")
        count_layout = QHBoxLayout(count_group)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(1, 16)
        self._slider.setValue(4)
        self._slider.setTickInterval(1)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._lbl_n = QLabel("4")
        self._lbl_n.setFixedWidth(24)
        self._slider.valueChanged.connect(
            lambda v: self._lbl_n.setText(str(v))
        )
        count_layout.addWidget(self._slider)
        count_layout.addWidget(self._lbl_n)
        layout.addWidget(count_group)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._btn_gen_single = QPushButton("Generate n images  (current type)")
        self._btn_gen_single.clicked.connect(self._on_gen_single)
        self._btn_gen_all = QPushButton(
            "Generate n × types  (all types from table)"
        )
        self._btn_gen_all.clicked.connect(self._on_gen_all)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_gen_single)
        btn_row.addWidget(self._btn_gen_all)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        # Pre-fill enhancement for the first type
        self._on_type_changed(0)
        return page

    def _build_progress_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addStretch()
        self._lbl_progress = QLabel("Starting…")
        self._lbl_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._lbl_progress)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)  # indeterminate
        layout.addWidget(self._progress_bar)
        layout.addStretch()

        self._btn_abort = QPushButton("Cancel Generation")
        self._btn_abort.clicked.connect(self._on_abort)
        layout.addWidget(self._btn_abort, 0, Qt.AlignmentFlag.AlignCenter)
        return page

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_type_changed(self, _index: int) -> None:
        key = self._cmb_type.currentData()
        if key and key in self._type_map:
            self._edit_enhancement.setPlainText(
                self._type_map[key]["prompt_enhancement"]
            )

    def _build_full_prompt(self, type_key: str) -> str:
        base = self._edit_prompt.toPlainText().strip()
        if type_key in self._type_map:
            enhancement = self._type_map[type_key]["prompt_enhancement"]
        else:
            enhancement = self._edit_enhancement.toPlainText().strip()
        parts = [p for p in [base, enhancement] if p]
        return ", ".join(parts)

    def _on_gen_single(self) -> None:
        pos_key = self._cmb_type.currentData() or ""
        sel_mod = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        enh = self._edit_enhancement.toPlainText().strip()
        base = self._edit_prompt.toPlainText().strip()
        n = self._slider.value()
        if sel_mod == "" and self._modifier_map:
            # (any) selected — one prompt per modifier type for this position
            prompts: list[tuple[str, str, str]] = []
            for mod_key, mod_info in self._modifier_map.items():
                mod_enh = mod_info.get("prompt_enhancement", "")
                parts = [p for p in [base, enh, mod_enh] if p]
                if parts:
                    prompts.append((", ".join(parts), pos_key, mod_key))
            if not prompts:
                return
            self._start_worker(prompts, n)
        else:
            mod_enh = self._modifier_map.get(sel_mod, {}).get("prompt_enhancement", "") if sel_mod else ""
            parts = [p for p in [base, enh, mod_enh] if p]
            prompt = ", ".join(parts)
            if not prompt:
                self._lbl_progress.setText("Please enter a prompt.")
                return
            self._start_worker([(prompt, pos_key, sel_mod)], n)

    def _on_gen_all(self) -> None:
        base = self._edit_prompt.toPlainText().strip()
        sel_mod = self._cmb_modifier.currentData() if self._cmb_modifier else ""
        n = self._slider.value()
        prompts: list[tuple[str, str, str]] = []
        if sel_mod == "" and self._modifier_map:
            # (any) selected — generate for every position × modifier combination
            for pos_key, pos_info in self._type_map.items():
                for mod_key, mod_info in self._modifier_map.items():
                    parts = [p for p in [base, pos_info["prompt_enhancement"],
                                         mod_info.get("prompt_enhancement", "")] if p]
                    if parts:
                        prompts.append((", ".join(parts), pos_key, mod_key))
        else:
            mod_enh = self._modifier_map.get(sel_mod, {}).get("prompt_enhancement", "") if sel_mod else ""
            for pos_key, pos_info in self._type_map.items():
                parts = [p for p in [base, pos_info["prompt_enhancement"], mod_enh] if p]
                if parts:
                    prompts.append((", ".join(parts), pos_key, sel_mod))
        if not prompts:
            return
        self._start_worker(prompts, n)

    def _start_worker(self, prompts: list[tuple[str, str, str]], n: int) -> None:
        self._stack.setCurrentIndex(1)
        self._lbl_progress.setText("Connecting to perchance.org…")
        self._worker = _GenerationWorker(prompts, n, self._output_dir)
        self._worker.progress.connect(self._lbl_progress.setText)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_done(self, pairs: list) -> None:
        _dlog("AiImageGenDialog._on_worker_done", f"{len(pairs)} images")
        self._worker = None
        if not pairs:
            show_error(
                self, "AI Generate",
                "No images were returned by perchance.org.\n"
                "Check your internet connection or try again later.",
                tag="AiImageGenDialog._on_worker_done",
            )
            self._stack.setCurrentIndex(0)
            return
        self.hide()
        paths = [p for p, _, _ in pairs]
        type_map = {p: (pk, mk) for p, pk, mk in pairs}
        picker = ImagePickerDialog(self.parent(), paths, self._on_accepted, type_map)
        picker.exec()
        self.accept()

    def _on_worker_error(self, msg: str) -> None:
        _dlog("AiImageGenDialog._on_worker_error", msg)
        self._worker = None
        show_error(
            self, "AI Generate",
            f"Image generation failed:\n{msg}\n\n"
            "Make sure you are connected to the internet.\n"
            "If the error persists, the perchance.org API may have changed.",
            tag="AiImageGenDialog._on_worker_error",
        )
        self._stack.setCurrentIndex(0)

    def _on_abort(self) -> None:
        if self._worker:
            self._worker.abort()
            self._worker.wait(3000)
            self._worker = None
        self._stack.setCurrentIndex(0)

    def closeEvent(self, event) -> None:
        if self._worker:
            self._worker.abort()
            self._worker.wait(3000)
        super().closeEvent(event)


# ─── Convenience launcher ─────────────────────────────────────────────────────

def open_ai_generate_dialog(
    parent: QWidget,
    widget_type: str,
    on_accepted: Callable[[dict], None],
    output_dir: str | None = None,
) -> None:
    """Show the AI image generation dialog for *widget_type*."""
    dlg = AiImageGenDialog(parent, widget_type, on_accepted, output_dir)
    dlg.exec()
