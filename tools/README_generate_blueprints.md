# generate_blueprints.py

Generates silhouette blueprint images from existing pack assets for use as
composition guides in AI image generation (img2img via AnythingXL).

For each canonical `(position, type)` combination, up to `--variants` source
images are selected from the pack `.ini` files (exact match preferred; falls
back to any image with the same position).  The character is removed with
[rembg](https://github.com/danielgatis/rembg) and replaced with a flat pink
silhouette; the background is partially desaturated.

Output: `src/assets/blueprints/<position>_<type>_<n>.png` (1024 × 1024 px PNG)

Positions and types are imported live from `src/modules/picture_widget.py`
(`SNAPSHOT_POSITIONS`, `LEWD_POSITIONS`, `SNAPSHOT_TYPES`, `LEWD_TYPES`).

## Requirements

```
pip install rembg onnxruntime pillow numpy scipy
```

These are already listed in `requirements.txt`.  On first run rembg downloads
the BRIA rmbg-2.0 model (~1 GB) to `%USERPROFILE%\.rembg\models\`.

## Usage

```bat
venv\Scripts\python.exe tools\generate_blueprints.py [options]
```

| Option | Default | Description |
| --- | --- | --- |
| `--roots DIR [DIR ...]` | both `tests/bonuscontent/exported/` sub-dirs | Pack directories, or parent directories containing packs, to scan. |
| `--out-dir DIR` | `src/assets/blueprints` | Output directory. |
| `--variants N` | `9` | Max blueprint variants per position+type slot. |
| `--size WxH` | `1024x1024` | Output image size in pixels. |
| `--color R G B` | `220 120 160` | Silhouette RGB fill colour (0–255 per channel). |
| `--alpha-threshold N` | `30` | rembg alpha threshold for the foreground mask (starting value for retries). |
| `--max-silhouette RATIO` | `0.70` | Reject an image if the silhouette covers more than this fraction of the canvas (0–1). |
| `--max-retries N` | `10` | Max parameter-adjustment retries per image before skipping it. |
| `--position POS [...]` | all canonical | Limit generation to specific positions. |
| `--type TYPE [...]` | all canonical | Limit generation to specific types. |
| `--overwrite` | — | Re-generate images that already exist (resets `n` to 1). |
| `--dry-run` | — | Print planned output without writing any files. |

## Silhouette coverage check

After rembg removes the background, the script measures what fraction of the
canvas is covered by the silhouette colour.  If the fraction exceeds
`--max-silhouette` (default 70 %), the parameters are tightened and the image
is retried — up to `--max-retries` times (default 10).  Each retry increases
the alpha threshold by 10, adds one erosion iteration, and widens the soft
blend ramp by 10.  The final coverage percentage is printed next to each
result line:

```
  angry_back_5.png ...
    retry 1/10: coverage 73.0% > 70% (thr=30 erode=2 ramp=40)
    retry 2/10: coverage 71.6% > 70% (thr=40 erode=3 ramp=50)
    -> {70%} OK
```

If all retries are exhausted the image is **skipped** (no file written) so
a subsequent run can attempt it with a different source image.

## Gap-filling on re-run

Skipped images leave gaps in the variant numbering.  Re-running the script
(without `--overwrite`) detects which variant slots are already filled and
attempts to generate only the missing ones — potentially from different source
images in the pool.

## Examples

Full generation (resumes automatically — skips existing files):

```bat
venv\Scripts\python.exe tools\generate_blueprints.py
```

Preview what would be generated:

```bat
venv\Scripts\python.exe tools\generate_blueprints.py --dry-run
```

**Incremental generation from a second pack folder:**  
Re-running with a different `--roots` fills in missing variants without
touching files that already exist.  If 5 variants were produced on the first
run, the second run adds `_6` through `_9`:

```bat
venv\Scripts\python.exe tools\generate_blueprints.py ^
    --roots "path\to\other\packs"
```

Regenerate only upskirt blueprints at reduced size:

```bat
venv\Scripts\python.exe tools\generate_blueprints.py ^
    --position upskirt ^
    --size 512x512 ^
    --overwrite
```

## Coverage

The script currently covers **27 of 31** canonical positions (the remaining 4
have no source images in the test pack set).  The full grid is
27 × 26 = **702 blueprints** (up to 9 variants each).
