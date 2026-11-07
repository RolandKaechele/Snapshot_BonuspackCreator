# Snapshot Pack Creator

The App is **not officially associated with Snapshot! or Tiny Secret Games**.

Desktop application for creating and editing bonus content packs for *Snapshot!*, *Snapshot: Lewd Shores*, and *Snapshot! Naughty Nightmares*.

Built with **Python 3.12** and **PyQt6**.

## Quick Start

1. Run `cli.bat` — it creates a virtual environment, installs dependencies, and opens a shell ready to use.
2. Launch the application:

```bat
venv\Scripts\python.exe src\main.py
```

Pass `--debug` to enable verbose debug logging.

## Building a Release

Additional one-time setup required before running `scons`:

```bat
REM PDF documentation (requires Ruby)
gem install asciidoctor-pdf

REM SFX installer — download "7-Zip Extra" from https://www.7-zip.org/download.html
REM and place 7zCon.sfx next to 7z.exe (e.g. C:\Program Files\7-Zip\7zCon.sfx)

REM Freeze tool
venv\Scripts\pip install pyinstaller
```

Then build:

```bat
venv\Scripts\python.exe -m scons
```

Produces `dist/SnapshotPackCreator_vYYYY-MM-DD_cu128_installer.exe`. The frozen app bundles CUDA 12.8 torch and falls back to CPU automatically at runtime when no NVIDIA GPU is present, so a separate CPU-only build is not needed (`scons torch=cpu` remains available if one is ever wanted).

## Features

- **Pack Info tab** — pack identity (ID, title, game, type, ID range), `[Defaults]` section values, special category with colour picker and badge preview, special type/color trait aliases; Discord link for requesting a unique ID range; Position/Type/Color dropdowns are editable so custom `[Special Traits]` alias tokens (e.g. `ghostHands`) round-trip instead of being silently replaced; the Category field is always shown regardless of the selected game
- **Game-aware UI** — three games are supported: *Snapshot!*, *Lewd Shores*, and *Naughty Nightmares*; selecting Lewd Shores or Naughty Nightmares hides the Snapshot!-only tabs (Cutscenes, Love Lens) automatically; the Events tab is available for Snapshot!, Naughty Nightmares, and Lewd Shores, relabelling itself to *Beach Events* (Pack Type combo entry included) when the selected game is Lewd Shores; game is also detected on import from `gameID`/`plugID` in `pack.ini` (`plugID=naughtynightmares` → Naughty Nightmares); City/Beach Events and Love Lens are additionally hidden unless *Pack Type* on the Pack Info tab matches (`Events` / `Love Lens`), since the game only reads those ini sections for the matching pack type; selecting Naughty Nightmares locks Pack Type to *Photos* (Events and Love Lens are not supported for that game)
- **Tooltips throughout** — every field and button carries a tooltip explaining its purpose and valid values
- Load / Save pack JSON project files
- Import and export bonus content folders
  - **Confirm before overwrite** — *New Pack* and *Import Bonus Content* prompt for confirmation when the current pack has unsaved changes; the prompt is skipped when there is nothing to lose
  - All views are cleared immediately when a new/import action is confirmed, before any new data is loaded, so no stale data from the previous pack lingers
  - Multi-ini bundle import: merges all `.ini` files in a pack folder; strips part-number suffixes from id and title; per-part `[Special Traits]` lists are preserved and restored on export so each exported ini contains only its original trait subset
  - `gameID`/`plugID` auto-detection from `[Mod]` / `[Pack]` on import (`plugID=naughtynightmares` → Naughty Nightmares, preserved verbatim on export)
  - `[Defaults]` and `[Events]` parsed into structured fields (not passthrough)
  - Large-pack export: automatically splits into numbered ini files (`mypack1.ini`, `mypack2.ini`, …) of up to 100 photos each with shifted ID ranges — unless the declared ID Range is already wide enough to cover every photo, in which case the pack is kept as a single `pack.ini` with that original range (matching official multi-100 packs like `murderclub`)
  - `[Special Traits]` (and the community aliases `[Special Type]`, `[Create your own traits]`) are normalised and re-emitted on export
  - Nested pack folder layouts (e.g. `PackFolder/PackFolder/Data/`) are searched automatically
- Photos tab — add / remove images (multi-select supported); position/type/color dropdowns are editable so custom alias tokens (e.g. Naughty Nightmares' `ghostHands`, `monster-cock-attack`) display and persist instead of resetting to the first entry; Naughty Nightmares has its own suggested Position/Type/Color vocabulary (e.g. `ghostHands`, `demon`, `werewolves`) instead of reusing the base Snapshot! lists; *`photoBooth`* position added; label corrections for `xBar`, `flasher`, `window`; newly added images auto-preselect Position from a `<value>_` filename prefix (case-insensitive, e.g. `upskirt_00010.png` → Upskirt Shot), matching the current game's position list; a *Naming Conventions…* button lists every prefix → label mapping for the current game; bulk trait editing — select multiple photos with Ctrl/Shift-click and change Position, Type, Color, or Overwrite labels for all at once; display-size combobox (Standard / Large / Very Large) switches the list between compact text mode and icon-grid mode; Love Lens `hypnoType` field shown when position = `hypno`; no image cap
  - `Position` values reserved for another Pack Type (`City Event Photo`, `Love Lens Photo`) are hidden from the dropdown unless that Pack Type is active; photos already using a mismatched position (e.g. imported from elsewhere) are marked with a ⚠ icon and reported in the Issue Report
  - A *Flag as Wrong…* button marks the selected photo as wrongly defined with corrected Position/Type/Color values and a free-text note; flagged photos show a ⚠ icon, export writes the *corrected* values to `pack.ini`, and the flag/correction/note are listed in the Issue Report
  - A *Filter* box above the list narrows it down by filename, position, type, or color (case-insensitive substring match)
  - A *Preprocess…* button resizes/recompresses selected photos (or all, if none selected) on disk via Pillow, given a max width/height and JPEG/PNG quality
  - **AI Generate** *(optional plugin, not bundled — install separately)* — generate images via a text-to-image API; choose a position and an optional photo type (plain, kinky, nude, …), enter a character prompt, and pick from the generated results; *(any)* photo-type iterates all modifier types automatically; generated images are tagged with position and type automatically; only user-selected images are copied to the pack folder
  - Game image formats `.dat`, `.jpa`, `.pna` (renamed JPEG/PNG) are previewed and imported correctly via content sniffing; `.byte` files (renamed MP4) are detected by magic bytes and shown in an inline video player widget
- Overwrite Texts — key/value editor for the `[Hypnosis Text]` dialogue section; each entry has a paired *Speaker* field (`key.tag=`, empty for narration) with sensible defaults (e.g. `hypno_start_mod.4` → `Woman`)
- City/Beach Events tab (Snapshot!, Naughty Nightmares, and Lewd Shores; Pack Type = Events only) — tab label and Pack Type entry switch to *Beach Events* for Lewd Shores; Backgrounds and Overlays with live image/video preview, reorder buttons, and a 3-pane Dialog editor (scene list / node list / node form)
  - Scene list: *New Scene…* creates a blank scene by name (no file needed); *Import Scene…* imports existing dialog JSON files from disk and auto-locates/registers any background/overlay assets the imported scene's own node commands reference; a *Template* dropdown (backed by `city_events_templates.json`, editable and shareable, filtered to the current game — untagged templates show for every game, `"game": "lewdshores"` templates only for Lewd Shores) plus *Add From Template* creates a scene pre-filled with starter content; right-click context menu offers New Scene…, Import Scene…, Rename…, Delete, and Save As Template… (which appends the selected scene's content back into the templates file, tagged with the current game when it is Lewd Shores)
  - Node form includes speaker dropdown (extended with `Schoolgirl`, `Teacher`, `Trio`), text, flow references (Next/Branch/Action) as dropdowns, and a command table with context-sensitive argument dropdowns and image/video browse/preview
  - Overlay commands: `mod_overlayImage3` is the legacy single overlay slot (images and MP4 video); `mod_overlayImage1` (bottom) and `mod_overlayImage2` (top) are independent image-only layers that can be shown together, used by Lewd Shores beach events
  - **Dialog Graph** button opens a visual node-graph editor where each node is a draggable coloured box with colour-coded arrows for the three flow connections (Next/Branch/Action); hold *Shift* and drag to rubber-band select multiple nodes, then *Ctrl+C*/*Ctrl+V* (or the Copy/Paste toolbar buttons) to duplicate them — pasted nodes keep their text/commands but have flow references cleared so they never silently merge into the existing branch
  - **Dialog Player** ("Test…") opens a step-through playback window that renders a composite preview of background, overlay layers, and dialog text box; `mod_overlayImage1`/`mod_overlayImage2` are rendered as simultaneous static-image layers, while `mod_overlayImage3` video overlays are decoded frame-by-frame and painted into the same composite canvas (so they never obscure the player-choice buttons) and loop continuously while active
  - Export-time validation blocks on flow-ref errors and warns on missing `endEvent`; warning dialog offers a checkbox to auto-inject `endEvent` into all affected scenes; a separate advisory warns if a pack has City/Beach Events content but Pack Type isn't set to Events
- Cutscenes tab — hidden (no released pack format supports cutscenes yet; will be re-enabled when the game defines the format)
- Love Lens tab (Snapshot!, Pack Type = Love Lens only) — tabbed Character Setup, 2D Overlay Slots, Texture Slots, and Result Photos (including the optional `Double Shot` result-photo type); overlay/texture slot previews detect `.bytes`/`.byte` MP4 overlay videos (e.g. `hypnoOverlay_*`) by content and play them inline instead of showing "Cannot preview"
- **Orphaned Files tab** — shows assets on disk that are not referenced by the pack (orphaned) and references in the ini that point to missing files (broken); for Events-type packs, broken references also include `mod_overlayImage1`/`mod_overlayImage2`/`mod_overlayImage3` and audio commands (`playSound`, `playSoundDelayed`, `stopLoopedSound`) referenced inside dialog scenes that resolve to neither a pack asset nor a builtin game asset; image preview for orphaned files; JSON dialog file preview (pretty-printed); delete orphaned files from disk; tab is hidden automatically when there is nothing to show- Plugin system — drop Python packages into `plugins/` to extend the application
  - **Manage Plugins…** (Tools menu) shows every discovered plugin in a table (Enabled checkbox / Name / Version / Status / Description); unchecking a plugin disables it, persisted to `plugin_config.json` and skipped on the next restart; plugins declaring a module-level `MIN_VRAM_GB` (e.g. `moss_image`, which needs ≈ 12 GB) show *Unsupported Hardware* with the checkbox greyed out when the detected GPU's VRAM is below it
- **Undo / Redo** (Edit menu, Ctrl+Z / Ctrl+Y) — a periodic snapshot timer captures the in-memory pack state so edits across Photos, Events, Love Lens, and the Dialog Graph can be undone/redone within the session
- **Auto-backup** — every *Save* also writes a timestamped copy to a `.backups/` folder beside the pack file (keeps the last 10); *File → Restore Previous Version…* lists them and restores one
- **Recent packs** — *File → Open Recent* remembers the last 10 opened/saved pack JSON files
- **Export as ZIP** — *File → Export Bonus Content as ZIP…* packages the exported BonusContent folder the same way official packs ship: contents wrapped in a top-level `<PackName>/` folder, plus a game-specific `README.txt` and a SHA-256 `manifest.json`, both at the zip root
- **Pack tools** (Tools menu)
  - *Find Duplicate Assets…* — hashes every photo/overlay/texture/event asset referenced by the pack and flags identical files
  - *Compare Packs…* — picks two saved pack JSON files and reports added/removed/changed photos, events, and pack-info fields
  - *Pack Statistics…* — counts of photos by position/type/color, missing-trait warnings, and event counts
  - *Generate Issue Report…* — writes a Markdown report of Position/Pack Type mismatches, photo ID registry conflicts, broken references, orphaned files, and manually flagged photos (see Photos tab and Orphaned Files tab above)
- Statusbar with live validation feedback
- Menubar with File / Edit / Tools / Help menus
- Double-click any image preview to open a zoomable full-resolution viewer; the viewer has a button to open the file in the system default editor
- Unified dialog helpers (`show_info`, `show_warning`, `show_error`, `show_confirm`, `show_confirm_with_checkbox`) with Copy-to-Clipboard on every dialog

## Folder Structure

```
├── .github/                    Copilot instruction files
├── docs/
│   ├── userguide/              End-user guide (AsciiDoc chapters)
│   ├── developerguide/         Developer guide (AsciiDoc chapters)
│   └── plugin-developerguide/  Plugin author guide (AsciiDoc chapters)
├── plugins/                    User-installed plugin packages
├── src/
│   ├── main.py                 Entry point    
|   ├── _version.py             Build version constant (patched by SConstruct; import `BUILD_VERSION`)│   
|   ├── app_debug.py            Debug flag and logging helper
│   ├── ui/
│   │   ├── main_window.py      QMainWindow shell; tab visibility by game
│   │   ├── menubar.py          Menubar builder
│   │   ├── statusbar.py        Statusbar controller
│   │   ├── image_viewer.py     Zoomable image viewer dialog; attach_viewer() helper
│   │   └── style.qss           Application stylesheet (Catppuccin Mocha)
│   └── modules/
|       ├── pack_manager.py     Load / Save pack JSON; dirty tracking (`is_dirty`); undo/redo (`push_history`/`undo`/`redo`); timestamped `.backups/` on save
│       ├── history_manager.py  JSON-snapshot undo/redo stack used by pack_manager.py
│       ├── recent_files.py     Recent-packs list (recent_packs.json)
│       ├── asset_dedup.py      SHA-256 duplicate-asset finder
│       ├── pack_diff.py        Pack-vs-pack JSON diff report
│       ├── pack_stats.py       Photo/event statistics dashboard
│       ├── zip_export.py       ZIP packaging (official folder layout + manifest.json)
│       ├── readme_templates.py README.txt template per game
│       ├── image_preprocess.py Pillow-based batch image resize/recompress
│       ├── import_export.py    Import / Export bonus content
│       ├── pack_info_widget.py Pack Info tab (identity, defaults, category, traits)
│       ├── tooltips.py         Central tooltip registry
│       ├── image_utils.py      Asset loading: load_pixmap, resolve_asset, ASSET_FILTER
│       ├── picture_widget.py   Photos tab
│       ├── overwrite_texts.py  Overwrite Texts tab
│       ├── event_widget.py     City Events tab
│       ├── city_events_templates.py  Load/save starter dialog scenes (city_events_templates.json)
│       ├── cutscene_widget.py  Cutscenes tab
│       ├── love_lens.py        Love Lens tab
│       ├── orphaned_files.py   Orphaned Files tab
│       ├── position_rules.py   Position values reserved for a specific Pack Type
│       ├── issue_report.py     Flag-as-Wrong dialog + Issue Report generation
│       ├── plugin_system.py    Plugin discovery and loader; disabled-plugin persistence
│       └── plugin_dialog.py    Manage Plugins enable/disable dialog
├── SConstruct                  SCons build script (freeze + docs → PDF + SFX installer)
├── LICENSE                     MIT license
├── tests/                      pytest test suite
├── temp/                       Portable Python runtime (not committed)
├── requirements.txt
└── cli.bat
```

## Pack Types

| Pack Type | Game | Tab visibility |
| --------- | ---- | --------------- |
| Regular Photos | Snapshot!, Lewd Shores, and Naughty Nightmares | — |
| Love Lens | Snapshot! only | Love Lens tab shown only when Pack Type = Love Lens |
| City/Beach Events | Snapshot!, Naughty Nightmares, Lewd Shores | City/Beach Events tab shown only when Pack Type = Events; tab relabels to *Beach Events* for Lewd Shores |
| Cutscenes | Snapshot! only | Cutscenes tab hidden (no released pack format yet) |

## Development

See `docs/developerguide/` for architecture details, module map, plugin API, and how to add new features.

Run tests:

```bat
venv\Scripts\python.exe -m pytest tests\ plugins\*\tests
```
