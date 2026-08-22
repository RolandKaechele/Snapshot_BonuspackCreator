# Snapshot Pack Creator

Desktop application for creating and editing bonus content packs for *Snapshot!* and *Snapshot: Lewd Shores*.

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

Produces `dist/SnapshotPackCreator_vYYYY-MM-DD_installer.exe`.

## Features

- **Pack Info tab** — pack identity (ID, title, game, type, ID range), `[Defaults]` section values, special category with colour picker and badge preview, special type/color trait aliases; Discord link for requesting a unique ID range
- **Game-aware UI** — selecting Lewd Shores hides the Snapshot!-only tabs (City Events, Cutscenes, Love Lens) automatically; game is also detected on import from `gameID` in `pack.ini`
- **Tooltips throughout** — every field and button carries a tooltip explaining its purpose and valid values
- Load / Save pack JSON project files
- Import and export bonus content folders
  - **Confirm before overwrite** — *New Pack* and *Import Bonus Content* prompt for confirmation when the current pack has unsaved changes; the prompt is skipped when there is nothing to lose
  - All views are cleared immediately when a new/import action is confirmed, before any new data is loaded, so no stale data from the previous pack lingers
  - Multi-ini bundle import: merges all `.ini` files in a pack folder; strips part-number suffixes from id and title; per-part `[Special Traits]` lists are preserved and restored on export so each exported ini contains only its original trait subset
  - `gameID` auto-detection from `[Mod]` / `[Pack]` on import
  - `[Defaults]` and `[Events]` parsed into structured fields (not passthrough)
  - Large-pack export: automatically splits into numbered ini files (`mypack1.ini`, `mypack2.ini`, …) of up to 100 photos each with shifted ID ranges
  - `[Special Traits]` (and the community aliases `[Special Type]`, `[Create your own traits]`) are normalised and re-emitted on export
  - Nested pack folder layouts (e.g. `PackFolder/PackFolder/Data/`) are searched automatically
- Photos tab — add / remove images (multi-select supported); position/type/color dropdowns; *`photoBooth`* position added; label corrections for `xBar`, `flasher`, `window`; bulk trait editing — select multiple photos with Ctrl/Shift-click and change Position, Type, Color, or Overwrite labels for all at once; display-size combobox (Standard / Large / Very Large) switches the list between compact text mode and icon-grid mode; Love Lens `hypnoType` field shown when position = `hypno`; no image cap
  - **AI Generate** — generate images via the perchance.org text-to-image API; choose a position and an optional photo type (plain, kinky, nude, …), enter a character prompt, and pick from the generated results; *(any)* photo-type iterates all modifier types automatically; generated images are tagged with position and type automatically; only user-selected images are copied to the pack folder; if Cloudflare Turnstile blocks the session a *Browser Verification* dialog opens the embed page in your real browser and guides you through a one-time DevTools Console paste step
  - Game image formats `.dat`, `.jpa`, `.pna` (renamed JPEG/PNG) are previewed and imported correctly via content sniffing; `.byte` files (renamed MP4) are detected by magic bytes and shown in an inline video player widget
- Overwrite Texts — override displayed trait labels per image
- City Events tab (Snapshot! only) — Backgrounds and Overlays with live image/video preview, reorder buttons, and a 3-pane Dialog editor (scene list / node list / node form); node form includes speaker dropdown (extended with `Schoolgirl`, `Teacher`, `Trio`), text, flow references (Next/Branch/Action) as dropdowns, and a command table with context-sensitive argument dropdowns and image/video browse/preview; **Dialog Graph** button opens a visual node-graph editor where each node is a draggable coloured box with colour-coded arrows for the three flow connections (Next/Branch/Action); **Dialog Player** opens a step-through playback window that renders a composite preview of background, overlay, and dialog text box; export-time validation blocks on flow-ref errors and warns on missing `endEvent`; warning dialog offers a checkbox to auto-inject `endEvent` into all affected scenes
- Cutscenes tab — hidden (no released pack format supports cutscenes yet; will be re-enabled when the game defines the format)
- Love Lens tab (Snapshot! only) — tabbed Character Setup, 2D Overlay Slots, Texture Slots, and Result Photos
- **Orphaned Files tab** — shows assets on disk that are not referenced by the pack (orphaned) and references in the ini that point to missing files (broken); image preview for orphaned files; JSON dialog file preview (pretty-printed); delete orphaned files from disk; tab is hidden automatically when there is nothing to show
- Plugin system — drop Python packages into `plugins/` to extend the application
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
        ├── pack_manager.py     Load / Save pack JSON; dirty tracking (`is_dirty`)
│       ├── import_export.py    Import / Export bonus content
│       ├── pack_info_widget.py Pack Info tab (identity, defaults, category, traits)
│       ├── tooltips.py         Central tooltip registry
│       ├── image_utils.py      Asset loading: load_pixmap, resolve_asset, ASSET_FILTER
│       ├── picture_widget.py   Photos tab
│       ├── overwrite_texts.py  Overwrite Texts tab
│       ├── event_widget.py     City Events tab
│       ├── cutscene_widget.py  Cutscenes tab
│       ├── love_lens.py        Love Lens tab
│       ├── orphaned_files.py   Orphaned Files tab
│       └── plugin_system.py    Plugin discovery and loader
├── SConstruct                  SCons build script (freeze + docs → PDF + SFX installer)
├── LICENSE                     MIT license
├── tests/                      pytest test suite
├── temp/                       Portable Python runtime (not committed)
├── requirements.txt
└── cli.bat
```

## Pack Types

| Pack Type | Game |
| --------- | ---- |
| Regular Photos | Snapshot! and Lewd Shores |
| Love Lens | Snapshot! only |
| City Events | Snapshot! only |
| Cutscenes | Snapshot! only |

## Development

See `docs/developerguide/` for architecture details, module map, plugin API, and how to add new features.

Run tests:

```bat
venv\Scripts\python.exe -m pytest tests\
```
