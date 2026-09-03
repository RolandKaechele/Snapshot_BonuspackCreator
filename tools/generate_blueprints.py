"""
generate_blueprints.py -- create silhouette blueprint images from pack assets.

Scans pack.ini files for canonical (position, type) pairs, then generates a
full grid of position x type blueprints.  For each slot, up to --variants
source images are selected (exact position+type match preferred; falls back to
any image with that position).  The character region is removed with rembg and
replaced with a flat silhouette colour; the background is partially desaturated.

Output files: <out-dir>/<position>_<type>_<n>.png  (1024x1024 px PNG)

Usage:
    venv\\Scripts\\python.exe tools\\generate_blueprints.py [options]

Options:
    --roots ROOT [ROOT ...]   Pack directories, or parent directories containing
                              packs, to scan (default: both test directories)
    --out-dir DIR             Output directory (default: src/assets/blueprints)
    --variants N              Max blueprint variants per position+type (default: 9)
    --size WxH                Output size in pixels (default: 1024x1024)
    --color R G B             Silhouette fill colour 0-255 (default: 220 120 160)
    --alpha-threshold N       rembg alpha threshold 0-255 (default: 30)
    --max-silhouette RATIO    reject image if silhouette covers more than this
                              fraction 0-1 (default: 0.70)
    --max-retries N           max parameter-adjustment retries per image (default: 10)
    --position POS [...]      Limit to specific positions (default: all canonical)
    --type TYPE [...]         Limit to specific types (default: all canonical)
    --overwrite               Re-generate images that already exist
    --dry-run                 Print planned output without generating images

Requires:
    pip install rembg onnxruntime pillow numpy scipy
"""

import argparse
import collections
import configparser
import os
import random
import re
import sys

# Import canonical value tables directly from the app module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from modules.picture_widget import (  # noqa: E402
    SNAPSHOT_POSITIONS, LEWD_POSITIONS,
    SNAPSHOT_TYPES, LEWD_TYPES,
)

_ALL_POSITIONS = frozenset(k for k, _ in SNAPSHOT_POSITIONS + LEWD_POSITIONS)
_ALL_TYPES = frozenset(SNAPSHOT_TYPES + LEWD_TYPES)

_IMAGE_EXTS = (".pna", ".dat", ".png", ".jpa")

_DEFAULT_ROOTS = [
    "tests/bonuscontent/exported/Snapshot!",
    "tests/bonuscontent/exported/Snapshot! LewdShores",
]

# ---------------------------------------------------------------------------
# INI parsing
# ---------------------------------------------------------------------------

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
    except configparser.Error:
        cp = configparser.RawConfigParser(strict=False)
        safe = "\n".join(l for l in lines if not re.match(r"^\s*\w[^=]*$", l))
        try:
            cp.read_string(safe)
        except configparser.Error:
            pass
    return cp


def _find_image(data_dir, name):
    for ext in _IMAGE_EXTS:
        path = os.path.join(data_dir, f"{name}{ext}")
        if os.path.isfile(path):
            return path
    return None


# ---------------------------------------------------------------------------
# Source collection
# ---------------------------------------------------------------------------

def collect_sources(roots, valid_positions, valid_types):
    """Return (exact[(pos,typ)], by_pos[pos]) with source image paths."""
    exact = collections.defaultdict(list)
    by_pos = collections.defaultdict(list)
    for root in roots:
        if not os.path.isdir(root):
            print(f"WARNING: root not found: {root}")
            continue
        if os.path.isfile(os.path.join(root, "pack.ini")):
            pack_dirs = [root]
        else:
            pack_dirs = [
                os.path.join(root, pack)
                for pack in sorted(os.listdir(root))
                if os.path.isfile(os.path.join(root, pack, "pack.ini"))
            ]
        for pack_dir in pack_dirs:
            ini = os.path.join(pack_dir, "pack.ini")
            cp = _parse_ini(ini)
            if not cp.has_section("Photos"):
                continue
            names_raw = cp.get("Photos", "names", fallback="")
            names = [n.strip() for n in names_raw.split(",") if n.strip()]
            def_pos = (cp.get("Defaults", "position", fallback="")
                       or cp.get("Defaults", "photoposition", fallback="")).strip()
            def_typ = cp.get("Defaults", "type", fallback="").strip()
            for name in names:
                pos = (cp.get("Photos", f"{name}.position", fallback=None)
                       or cp.get("Photos", f"{name}.photoposition", fallback=None)
                       or def_pos).strip()
                typ = (cp.get("Photos", f"{name}.type", fallback=None) or def_typ).strip()
                if pos not in valid_positions:
                    continue
                img = _find_image(os.path.join(pack_dir, "Data"), name)
                if not img:
                    continue
                by_pos[pos].append(img)
                # only record exact match when type is valid and not a position key
                if typ in valid_types and typ not in valid_positions:
                    exact[(pos, typ)].append(img)
    return dict(exact), dict(by_pos)


# ---------------------------------------------------------------------------
# Image processing
# ---------------------------------------------------------------------------

_MAX_SILHOUETTE_RATIO = 0.70  # reject if silhouette covers more than this fraction
_MAX_RETRIES = 10


def _build_silhouette(fg_rgba, alpha_threshold, erosion_iters, soft_ramp, color_rgba):
    """Return (silhouette_arr, coverage_ratio). Does not write any file."""
    import numpy as np
    from scipy.ndimage import binary_erosion

    fg_arr = np.array(fg_rgba)
    alpha = fg_arr[:, :, 3].astype(np.float32)

    hard_mask = alpha > alpha_threshold
    if erosion_iters > 0:
        hard_mask = binary_erosion(hard_mask, iterations=erosion_iters)

    soft_alpha = np.clip((alpha - alpha_threshold) / max(soft_ramp, 1), 0.0, 1.0)
    soft_alpha[~hard_mask] = 0.0

    coverage = float(hard_mask.sum()) / hard_mask.size

    silhouette = np.zeros_like(fg_arr)
    silhouette[:, :, :3] = color_rgba[:3]
    silhouette[:, :, 3] = (soft_alpha * 255).astype(np.uint8)
    return silhouette, coverage


def make_silhouette(src_path, out_path, size, color_rgba, alpha_threshold,
                    max_silhouette=_MAX_SILHOUETTE_RATIO, max_retries=_MAX_RETRIES):
    try:
        from PIL import Image
        import numpy as np
        from rembg import remove as rembg_remove
    except ImportError as e:
        print(f"  MISSING DEPENDENCY: {e}")
        print("  Install with: pip install rembg onnxruntime pillow numpy scipy")
        return False, 0.0

    try:
        src = Image.open(src_path).convert("RGBA").resize(size, Image.LANCZOS)
    except Exception as e:
        print(f"  Cannot open {src_path}: {e}")
        return False, 0.0

    try:
        fg_rgba = rembg_remove(src)
    except Exception as e:
        print(f"  rembg failed on {src_path}: {e}")
        return False, 0.0

    # Retry with increasing erosion/threshold until coverage drops below the limit
    silhouette = None
    best = None  # (coverage, silhouette) — best attempt so far
    for attempt in range(max_retries):
        # Each retry: raise threshold by 10, add 1 erosion iteration, widen soft ramp by 10
        threshold = alpha_threshold + attempt * 10
        erosion = 2 + attempt
        ramp = 40 + attempt * 10
        sil, ratio = _build_silhouette(fg_rgba, threshold, erosion, ramp, color_rgba)
        if best is None or ratio < best[0]:
            best = (ratio, sil)
        if ratio <= max_silhouette:
            silhouette = sil
            break
        print(f"    retry {attempt + 1}/{max_retries}: coverage {ratio:.1%} > {max_silhouette:.0%}"
              f" (thr={threshold} erode={erosion} ramp={ramp})", flush=True)

    if silhouette is None:
        # All retries exhausted — use the attempt with lowest coverage and warn
        ratio, silhouette = best
        print(f"    WARNING: could not reduce coverage below {max_silhouette:.0%}"
              f" (best {ratio:.1%}), skipping image.")
        return False, ratio

    import numpy as np
    bg_arr = np.array(src.convert("RGB"), dtype=np.float32)
    grey = bg_arr.mean(axis=2, keepdims=True)
    bg_arr = np.clip((grey * 0.6 + bg_arr * 0.4) * 1.15, 0, 255).astype(np.uint8)
    bg_rgba_arr = np.dstack([bg_arr, np.full((*bg_arr.shape[:2], 1), 255, dtype=np.uint8)])

    from PIL import Image
    composite = Image.alpha_composite(
        Image.fromarray(bg_rgba_arr, "RGBA"),
        Image.fromarray(silhouette.astype(np.uint8), "RGBA"),
    ).convert("RGB")

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    composite.save(out_path)
    return True, ratio


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args():
    p = argparse.ArgumentParser(
        description="Generate silhouette blueprint images from pack assets."
    )
    p.add_argument("--roots", nargs="+", default=_DEFAULT_ROOTS,
                   metavar="DIR",
                   help="Pack root directories to scan.")
    p.add_argument("--out-dir", default="src/assets/blueprints",
                   metavar="DIR",
                   help="Output directory for blueprint images.")
    p.add_argument("--variants", type=int, default=9,
                   metavar="N",
                   help="Max blueprint variants per position+type slot (default: 9).")
    p.add_argument("--size", default="1024x1024",
                   metavar="WxH",
                   help="Output image size (default: 1024x1024).")
    p.add_argument("--color", nargs=3, type=int, default=[220, 120, 160],
                   metavar=("R", "G", "B"),
                   help="Silhouette RGB fill colour 0-255 (default: 220 120 160).")
    p.add_argument("--alpha-threshold", type=int, default=30,
                   metavar="N",
                   help="rembg alpha threshold for foreground mask (default: 30).")
    p.add_argument("--position", nargs="+", default=None,
                   metavar="POS",
                   help="Limit to specific positions (default: all canonical).")
    p.add_argument("--type", nargs="+", default=None, dest="types",
                   metavar="TYPE",
                   help="Limit to specific types (default: all canonical).")
    p.add_argument("--max-silhouette", type=float, default=0.70,
                   metavar="RATIO",
                   help="Reject if silhouette covers more than this fraction 0-1 (default: 0.70).")
    p.add_argument("--max-retries", type=int, default=10,
                   metavar="N",
                   help="Max parameter-adjustment retries per image before skipping (default: 10).")
    p.add_argument("--overwrite", action="store_true",
                   help="Re-generate images that already exist.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print planned output without generating images.")
    return p.parse_args()


def main():
    args = _parse_args()

    w, h = (int(v) for v in args.size.lower().split("x"))
    size = (w, h)
    color_rgba = tuple(args.color) + (255,)

    valid_positions = (frozenset(args.position) & _ALL_POSITIONS) if args.position else _ALL_POSITIONS
    valid_types = (frozenset(args.types) & _ALL_TYPES) if args.types else _ALL_TYPES

    if args.position:
        unknown = set(args.position) - _ALL_POSITIONS
        if unknown:
            print(f"WARNING: unknown positions ignored: {sorted(unknown)}")
    if args.types:
        unknown = set(args.types) - _ALL_TYPES
        if unknown:
            print(f"WARNING: unknown types ignored: {sorted(unknown)}")

    exact, by_pos = collect_sources(args.roots, valid_positions, valid_types)
    positions_found = sorted(by_pos.keys())

    print(f"Positions with source images : {len(positions_found)}/{len(valid_positions)}")
    print(f"Exact (pos,type) pairs found : {len(exact)}")
    print(f"Full grid                    : {len(positions_found)} x {len(valid_types)} "
          f"= {len(positions_found) * len(valid_types)} blueprints planned")

    total_planned = total_done = 0
    no_source = []

    for pos in positions_found:
        for typ in sorted(valid_types):
            sources = exact.get((pos, typ)) or by_pos.get(pos, [])
            if not sources:
                no_source.append(f"{pos}_{typ}")
                continue
            fallback = "" if (pos, typ) in exact else " [pos-fallback]"
            if args.overwrite:
                n_start = 1
                slots_needed = args.variants
            else:
                # count existing variants so a second run fills in the gaps
                n_start = sum(
                    1 for i in range(1, args.variants + 1)
                    if os.path.isfile(os.path.join(args.out_dir, f"{pos}_{typ}_{i}.png"))
                ) + 1
                slots_needed = args.variants - (n_start - 1)
            if slots_needed <= 0:
                total_planned += n_start - 1
                total_done += n_start - 1
                continue
            sample = random.sample(sources, min(slots_needed, len(sources)))
            n = n_start
            for src in sample:
                out = os.path.join(args.out_dir, f"{pos}_{typ}_{n}.png")
                total_planned += 1
                if args.dry_run:
                    print(f"  [dry]{fallback} {pos}_{typ}_{n}.png  <- {src}")
                    n += 1
                else:
                    print(f"  {pos}_{typ}_{n}.png{fallback} ...", flush=True)
                    ok, ratio = make_silhouette(src, out, size, color_rgba, args.alpha_threshold,
                                                  args.max_silhouette, args.max_retries)
                    if ok:
                        print(f"    -> {{{ratio:.0%}}} OK")
                        total_done += 1
                        n += 1
                    else:
                        print("FAILED")

    if no_source:
        print(f"\nNo source images for {len(no_source)} pairs (position has no pack data).")

    if args.dry_run:
        print(f"\nDry run: would generate {total_planned} blueprint images.")
    else:
        print(f"\nDone: {total_done}/{total_planned} blueprints generated -> {args.out_dir}/")


if __name__ == "__main__":
    main()
