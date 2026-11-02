"""Tests for zip_export (official-matching folder layout) and readme_templates."""

import json
import os
import zipfile

from modules.zip_export import export_folder_as_zip
from modules.readme_templates import build_readme


def _make_pack_folder(tmp_path, name: str) -> str:
    pack_folder = str(tmp_path / name)
    data_folder = os.path.join(pack_folder, "Data")
    os.makedirs(data_folder, exist_ok=True)
    with open(os.path.join(pack_folder, "pack.ini"), "w", encoding="utf-8") as f:
        f.write("[Mod]\nplugID=snapshot\n")
    with open(os.path.join(data_folder, "photo1.dat"), "wb") as f:
        f.write(b"fake-image-bytes")
    return pack_folder


def test_zip_wraps_contents_in_pack_name_folder(tmp_path):
    pack_folder = _make_pack_folder(tmp_path, "Snapshot_BonusPack_Test")
    zip_path = str(tmp_path / "out.zip")
    export_folder_as_zip(pack_folder, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert "Snapshot_BonusPack_Test/pack.ini" in names
    assert "Snapshot_BonusPack_Test/Data/photo1.dat" in names


def test_zip_readme_and_manifest_sit_at_zip_root(tmp_path):
    pack_folder = _make_pack_folder(tmp_path, "Snapshot_BonusPack_Test")
    zip_path = str(tmp_path / "out.zip")
    export_folder_as_zip(pack_folder, zip_path, readme_text=build_readme("snapshot"))

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        assert "README.txt" in names
        assert "manifest.json" in names
        readme = zf.read("README.txt").decode("utf-8")
        manifest = json.loads(zf.read("manifest.json"))

    assert "Snapshot! Bonus Content Pack" in readme
    assert "Import Packages" in readme
    assert "Snapshot_BonusPack_Test/Data/photo1.dat" in manifest["files"]


def test_zip_without_readme_text_has_no_readme_entry(tmp_path):
    pack_folder = _make_pack_folder(tmp_path, "Snapshot_BonusPack_Test")
    zip_path = str(tmp_path / "out.zip")
    export_folder_as_zip(pack_folder, zip_path)

    with zipfile.ZipFile(zip_path) as zf:
        assert "README.txt" not in zf.namelist()


def test_build_readme_mentions_game_title():
    assert "Snapshot: Lewd Shores" in build_readme("lewdshores")
    assert "Snapshot! Naughty Nightmares" in build_readme("naughtynightmares")
    assert "Snapshot!" in build_readme("snapshot")


def test_build_readme_includes_discord_link():
    readme = build_readme("snapshot")
    assert "https://discord.com/invite/KtRr4WSyks" in readme
