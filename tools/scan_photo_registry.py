"""
scan_photo_registry.py -- build/update a JSON registry of photo IDs used across bonus packs.

Scans an input folder recursively for pack .ini files (pack.ini, pack1.ini, ...) belonging to
Snapshot! or Lewd Shores bonus content packages. For each pack found, the numeric photo ID
assigned to every photo is computed as ``idrange start + index`` (matching the order photos are
listed in ``[Photos] names``), and recorded together with the game ID, pack name and photo name
in a registry JSON file. The registry lets the app's Pack Info "Identity" tab verify that a
pack's photo IDs are not already used by another scanned pack.

Usage:
    venv\\Scripts\\python.exe tools\\scan_photo_registry.py --input FOLDER [options]

Options:
    --input FOLDER    Folder to scan recursively for pack .ini files (required)
    --registry FILE   Registry JSON file to update (default: src/registry.json)
    --dry-run         Scan only; print a summary without writing the registry file
"""

import argparse
import configparser
import os
import re
import sys

# Import the shared registry helpers directly from the app module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from modules.photo_registry import (  # noqa: E402
    default_registry_path, load_registry, save_registry, merge_pack_entries,
)


def _parse_args():
    p = argparse.ArgumentParser(
        description="Scan bonus content packs for photo IDs and build/update a JSON registry."
    )
    p.add_argument("--input", required=True,
                   help="Folder to scan recursively for pack .ini files.")
    p.add_argument("--registry", default=None,
                   help="Registry JSON file to update (default: src/registry.json).")
    p.add_argument("--dry-run", action="store_true",
                   help="Scan only; print a summary without writing the registry file.")
    return p.parse_args()


def _read_ini_lines(path):
    lines = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if line and line[0] in (" ", "\t") and lines:
                lines[-1] = lines[-1].rstrip("\n") + " " + line.lstrip()
            else:
                lines.append(line)
    return lines


def _parse_ini(path):
    lines = _read_ini_lines(path)
    cp = configparser.RawConfigParser(strict=False)
    try:
        cp.read_string("".join(lines))
        return cp
    except configparser.Error:
        safe = "\n".join(l for l in lines if not re.match(r"^\s*\w[^=]*$", l))
        cp = configparser.RawConfigParser(strict=False)
        try:
            cp.read_string(safe)
            return cp
        except configparser.Error:
            return None


def _find_ini_files(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name.lower().endswith(".ini"):
                yield os.path.join(dirpath, name)


def _extract_pack_photos(ini_path):
    """Return (game_id, pack_name, id_start, [photo_name, ...]) or None if not a pack ini."""
    cfg = _parse_ini(ini_path)
    if cfg is None:
        return None

    section = next((s for s in ("Mod", "Pack") if cfg.has_section(s)), None)
    if section is None:
        return None

    game_id = "snapshot"
    for opt in ("gameid", "gameID"):
        if cfg.has_option(section, opt):
            if cfg.get(section, opt).strip().lower() == "lewdshores":
                game_id = "lewdshores"
            break

    if not cfg.has_option(section, "id"):
        return None
    pack_name = cfg.get(section, "id").strip()
    if not pack_name:
        return None

    if not cfg.has_option(section, "idrange"):
        return None
    id_range = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", cfg.get(section, "idrange"))
    if not id_range:
        return None
    id_start = int(id_range.group(1))

    if not cfg.has_option("Photos", "names"):
        return None
    photo_names = [n.strip() for n in cfg.get("Photos", "names").split(",") if n.strip()]
    if not photo_names:
        return None

    return game_id, pack_name, id_start, photo_names


def scan_folder(root):
    """Return a list of (game_id, pack_name, id_start, photo_names, source_ini) per pack ini found."""
    packs = []
    for ini_path in sorted(_find_ini_files(root)):
        result = _extract_pack_photos(ini_path)
        if result is None:
            continue
        game_id, pack_name, id_start, photo_names = result
        packs.append((game_id, pack_name, id_start, photo_names, ini_path))
    return packs


def main():
    args = _parse_args()
    registry_path = args.registry or default_registry_path()

    if not os.path.isdir(args.input):
        print(f"Input folder not found: {args.input}")
        sys.exit(1)

    packs = scan_folder(args.input)

    print(f"Scanned            : {args.input}")
    print(f"Pack ini files      : {len(packs)}")
    print(f"Photo IDs found     : {sum(len(p[3]) for p in packs)}")
    for game_id, pack_name, id_start, photo_names, ini_path in packs:
        rel = os.path.relpath(ini_path, args.input)
        print(f"  [{game_id}] {pack_name}: {len(photo_names)} photos starting at {id_start}  ({rel})")

    if args.dry_run:
        print("Dry run — registry not written.")
        return

    # Group by (game_id, pack_name) first: multi-part packs (pack1.ini, pack2.ini, ...)
    # share the same id but must not overwrite each other's photos on merge.
    # Dedupe by photo_id within a group so identical duplicate ini files collapse to one entry.
    grouped: dict[tuple[str, str], dict[int, tuple[str, str]]] = {}
    for game_id, pack_name, id_start, photo_names, ini_path in packs:
        by_photo_id = grouped.setdefault((game_id, pack_name), {})
        for offset, name in enumerate(photo_names):
            by_photo_id[id_start + offset] = (name, ini_path)

    registry = load_registry(registry_path)
    for (game_id, pack_name), by_photo_id in grouped.items():
        photo_ids = [(photo_id, name) for photo_id, (name, _ini_path) in by_photo_id.items()]
        sources = sorted({os.path.relpath(ini_path, args.input) for _name, ini_path in by_photo_id.values()})
        registry = merge_pack_entries(
            registry, game_id, pack_name, photo_ids, source=", ".join(sources),
        )

    save_registry(registry, registry_path)
    print(f"Registry updated   : {registry_path}")
    print(f"Total entries      : {len(registry['entries'])}")


if __name__ == "__main__":
    main()
