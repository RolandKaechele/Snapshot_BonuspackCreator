"""Tests for modules/archive_import.py — archive extraction for bonus content import."""

import os
import zipfile

import pytest

from modules.archive_import import (
    ArchiveImportError,
    extract_archive_to_temp,
)


def _make_zip(tmp_path, wrap_in_subfolder: bool, extra_root_file: bool = False) -> str:
    zip_path = os.path.join(tmp_path, "pack.zip")
    prefix = "MyPack/" if wrap_in_subfolder else ""
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(f"{prefix}pack.ini", "[Mod]\nid=mypack\ntitle=\"My Pack\"\n")
        zf.writestr(f"{prefix}Data/photo1.png", b"fakeimagedata")
        if extra_root_file:
            zf.writestr("README.txt", "hello")
    return zip_path


def test_extract_zip_descends_into_single_wrapper_folder(tmp_path):
    zip_path = _make_zip(tmp_path, wrap_in_subfolder=True)
    folder = extract_archive_to_temp(zip_path)
    assert os.path.isfile(os.path.join(folder, "pack.ini"))
    assert os.path.isfile(os.path.join(folder, "Data", "photo1.png"))


def test_extract_zip_descends_with_loose_root_file(tmp_path):
    zip_path = _make_zip(tmp_path, wrap_in_subfolder=True, extra_root_file=True)
    folder = extract_archive_to_temp(zip_path)
    assert os.path.isfile(os.path.join(folder, "pack.ini"))


def test_extract_zip_flat_layout_stays_at_root(tmp_path):
    zip_path = _make_zip(tmp_path, wrap_in_subfolder=False)
    folder = extract_archive_to_temp(zip_path)
    assert os.path.isfile(os.path.join(folder, "pack.ini"))


def test_extract_rejects_unsupported_extension(tmp_path):
    bogus = os.path.join(tmp_path, "pack.7z")
    with open(bogus, "wb") as f:
        f.write(b"not an archive")
    with pytest.raises(ArchiveImportError):
        extract_archive_to_temp(bogus)


def test_extract_zip_rejects_path_traversal(tmp_path):
    zip_path = os.path.join(tmp_path, "evil.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../../evil.txt", "pwned")
    with pytest.raises(ArchiveImportError):
        extract_archive_to_temp(zip_path)
