---
applyTo: "**"
---

## Scripting & Shell Rules

- **Use `.bat` files or `cmd` commands** for all shell scripts — do NOT suggest PowerShell scripts (`.ps1`); they have UTF-8 encoding issues on Windows.
- **Never use PowerShell to edit any project file** — `Get-Content`, `Set-Content`, `Out-File`, and `>` redirection in PowerShell all silently re-encode UTF-8 as cp1252 on German Windows. Use `venv\Scripts\python.exe` for all file manipulation instead.
- Batch variable expansion inside loops/blocks requires `setlocal enabledelayedexpansion` and `!VAR!` syntax.
- `%~dp0` is the script directory in batch files.

## Encoding

- All `.py`, `.qss`, `.md`, `.adoc`, `.json`, `.ini` files must be saved as **UTF-8 without BOM**.
- When writing files from Python: always pass `encoding="utf-8"` to `open()`.

## Version Control

- This project is tracked in **both** Git and SVN (dual working copy — `.git` and `.svn` both present at the workspace root). Keep both in sync for every change.
- **Never commit** the `venv/`, `temp/`, or `.pycache/` directories.
- **Renaming/moving any file (source, docs, or test files) must use `svn move`/`svn rename` and `git mv`/`git add -A` — never a plain OS delete+create (e.g. `create_file` + delete) or `Move-Item` alone.** Plain renames lose each tool's history tracking.
  - Since this is a single working copy mirrored by both VCS, you cannot run `git mv` and `svn move` back-to-back on the same path (the second one will fail, since the file is already gone from its old location). Instead:
    1. Run `svn move <old> <new>` first — this performs the actual on-disk rename and schedules it in SVN.
    2. Then run `git add -A -- <old> <new>` so Git stages the resulting delete+add; `git status` will show it as `R` (renamed) because Git detects renames by content similarity at diff time, not by an explicit "move" operation.
  - This applies to test files too — renaming `tests/**` files must go through the same `svn move` + `git add -A` sequence, not a fresh `create_file`/delete.
  - Files that are new/untracked in both VCS (never committed) have no history to preserve — a plain filesystem rename (`Move-Item`) is fine for those; just rename before staging/adding.
  - Never run `svn commit` or `git commit`/`git push` automatically — stop after making the renames/edits and suggest a commit message; the user commits manually.
