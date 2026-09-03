# scan_photo_registry.py

Scans an input folder recursively for bonus content pack `.ini` files (`pack.ini`,
`pack1.ini`, ...) and builds/updates a JSON registry of every photo ID in use, so
new packs can be checked for ID collisions before publishing.

For each pack `.ini` found, the game ID (`snapshot` or `lewdshores`), pack name
(`[Mod]`/`[Pack]` `id=`) and photo names (`[Photos]` `names=`) are read. Photo IDs
are computed the same way the game assigns them: sequentially starting at the
`idrange=` start value, in the order photos are listed.

Output: `src/registry.json` (default), a list of `{game_id, pack_name, photo_id, photo_name, source}` entries, one per photo.

Re-running the scan replaces the entries for any pack whose `(game_id, pack_name)`
is found again, so the registry stays in sync when re-scanning the same input
folder after packs change.

## Usage

```bat
venv\Scripts\python.exe tools\scan_photo_registry.py --input FOLDER [options]
```

| Option | Default | Description |
| --- | --- | --- |
| `--input FOLDER` | *(required)* | Folder to scan recursively for pack `.ini` files. |
| `--registry FILE` | `src/registry.json` | Registry JSON file to update. |
| `--dry-run` | off | Scan only; print a summary without writing the registry file. |

## App integration

The Pack Info → **Identity** tab has a **✓ Verify Photo IDs** button that loads
`src/registry.json` and reports any photo IDs in the current pack's ID range
that are already used by a different pack recorded in the registry. Run this
script first to populate the registry from your installed/exported packs.
