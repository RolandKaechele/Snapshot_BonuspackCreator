"""Tests for modules.image_utils — path helpers."""

import os

from modules.image_utils import assets_root, game_asset_dir


def test_assets_root_points_to_src_assets():
    root = assets_root()
    assert os.path.basename(root) == "assets"
    assert os.path.isdir(root)


def test_game_asset_dir_is_under_assets_root():
    d = game_asset_dir("Texture2D", "snapshot")
    assert d.startswith(assets_root())
