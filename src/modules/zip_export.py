"""ZIP export — package an exported BonusContent folder with a checksum manifest."""

import hashlib
import json
import os
import zipfile

from app_debug import dlog as _dlog


def export_folder_as_zip(folder: str, zip_path: str, readme_text: str | None = None) -> str:
    """Zip *folder* into *zip_path*, matching the official Bonus Content pack
    layout: all files sit under a top-level folder named after *folder*
    (e.g. ``Snapshot_BonusPack_MyPack/Data/...``), with an optional
    ``README.txt`` and a ``manifest.json`` checksum file at the zip root,
    alongside the pack folder (not inside it). Returns *zip_path*."""
    pack_name = os.path.basename(folder.rstrip(os.sep).rstrip("/"))
    manifest: dict[str, str] = {}
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(folder):
            for name in files:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, folder)
                arcname = f"{pack_name}/{rel}".replace(os.sep, "/")
                zf.write(full, arcname)
                manifest[arcname] = _sha256_of(full)
        if readme_text:
            zf.writestr("README.txt", readme_text)
        zf.writestr("manifest.json", json.dumps({"files": manifest}, indent=2))
    _dlog("zip_export.export_folder_as_zip", f"Packaged {len(manifest)} file(s) -> {zip_path}")
    return zip_path


def _sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
