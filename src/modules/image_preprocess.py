"""Batch image preprocessing — resize/compress photo files on disk via Pillow."""

import os

from app_debug import dlog as _dlog


def preprocess_image_file(
    path: str, max_width: int | None, max_height: int | None, quality: int,
) -> bool:
    """Downscale *path* in place so it fits within max_width x max_height
    (aspect ratio preserved, never upscaled) and re-save with *quality*
    compression. Returns True if the file was modified, False otherwise
    (already within bounds, unsupported format, or missing file)."""
    if not path or not os.path.isfile(path):
        return False
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        _dlog("image_preprocess.preprocess_image_file", "Pillow not installed")
        return False

    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:
        _dlog("image_preprocess.preprocess_image_file", f"cannot open {path!r}: {exc}")
        return False

    orig_w, orig_h = img.size
    new_w, new_h = orig_w, orig_h
    if max_width and new_w > max_width:
        new_h = round(new_h * (max_width / new_w))
        new_w = max_width
    if max_height and new_h > max_height:
        new_w = round(new_w * (max_height / new_h))
        new_h = max_height

    resized = (new_w, new_h) != (orig_w, orig_h)
    if not resized and quality >= 100:
        return False

    if resized:
        img = img.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)

    save_kwargs = {}
    fmt = (img.format or "").upper()
    ext = os.path.splitext(path)[1].lower()
    if fmt in ("JPEG", "JPG") or ext in (".jpg", ".jpeg"):
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
    elif fmt == "PNG" or ext == ".png":
        save_kwargs["optimize"] = True

    try:
        img.save(path, **save_kwargs)
    except Exception as exc:
        _dlog("image_preprocess.preprocess_image_file", f"save failed for {path!r}: {exc}")
        return False
    _dlog("image_preprocess.preprocess_image_file",
          f"{path}: {orig_w}x{orig_h} -> {new_w}x{new_h}")
    return True
