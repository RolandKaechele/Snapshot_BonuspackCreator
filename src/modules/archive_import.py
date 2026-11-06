"""Archive import — extracts a .zip/.rar bonus content pack to a temp folder."""

import os
import shutil
import subprocess
import tempfile
import zipfile

from app_debug import dlog as _dlog

ARCHIVE_FILTER = "Archives (*.zip *.rar);;ZIP files (*.zip);;RAR files (*.rar);;All files (*)"

_TEMP_PREFIX = "snapshot_pack_import_"


class ArchiveImportError(Exception):
    pass


def extract_archive_to_temp(archive_path: str) -> str:
    """Extract *archive_path* (.zip or .rar) into a fresh temp folder and return
    the folder that actually holds the pack contents (descending into a single
    top-level subfolder when the archive wraps everything in one, which is how
    official Bonus Content packs are structured). The temp folder is left on
    disk for the lifetime of the imported pack (its assets are referenced from
    there) and is not deleted automatically — the OS temp-cleanup process or a
    manual cleanup takes care of stale ones over time."""
    ext = os.path.splitext(archive_path)[1].lower()
    dest = tempfile.mkdtemp(prefix=_TEMP_PREFIX)
    try:
        if ext == ".zip":
            _extract_zip(archive_path, dest)
        elif ext == ".rar":
            _extract_rar(archive_path, dest)
        else:
            raise ArchiveImportError(f"Unsupported archive type: {ext}")
    except ArchiveImportError:
        shutil.rmtree(dest, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(dest, ignore_errors=True)
        raise ArchiveImportError(f"Failed to extract archive:\n{exc}") from exc

    pack_folder = _descend_single_subfolder(dest)
    _dlog("archive_import.extract_archive_to_temp", f"{archive_path} -> {pack_folder}")
    return pack_folder


def _extract_zip(archive_path: str, dest: str) -> None:
    with zipfile.ZipFile(archive_path) as zf:
        _check_members_safe(zf.namelist(), dest)
        zf.extractall(dest)


def _extract_rar(archive_path: str, dest: str) -> None:
    exe = _find_7zip_exe()
    if not exe:
        raise ArchiveImportError(
            "RAR archives require 7-Zip to be installed (not found at the usual "
            "install location or on PATH). Install 7-Zip, or extract the archive "
            "manually and use 'Import Bonus Content…' on the extracted folder."
        )
    result = subprocess.run(
        [exe, "x", "-y", f"-o{dest}", archive_path],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        raise ArchiveImportError(
            f"7-Zip failed to extract the RAR archive (exit code {result.returncode}):\n"
            f"{result.stderr.strip() or result.stdout.strip()}"
        )


def _check_members_safe(names: list[str], dest: str) -> None:
    """Reject zip entries that would escape *dest* (zip-slip protection)."""
    dest_abs = os.path.abspath(dest)
    for name in names:
        target = os.path.abspath(os.path.join(dest, name))
        if not (target == dest_abs or target.startswith(dest_abs + os.sep)):
            raise ArchiveImportError(f"Archive contains an unsafe path: {name}")


def _descend_single_subfolder(folder: str) -> str:
    """If *folder* has no .ini file of its own but contains exactly one
    subdirectory, return that subdirectory instead — archives typically wrap
    the pack in one top-level folder, sometimes alongside loose files like a
    README.txt that aren't part of the pack."""
    entries = os.listdir(folder)
    if any(e.lower().endswith(".ini") for e in entries):
        return folder
    subdirs = [e for e in entries if os.path.isdir(os.path.join(folder, e))]
    if len(subdirs) == 1:
        return os.path.join(folder, subdirs[0])
    return folder


def _find_7zip_exe() -> str | None:
    found = shutil.which("7z") or shutil.which("7z.exe")
    if found:
        return found
    for candidate in (
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ):
        if os.path.exists(candidate):
            return candidate
    return None
