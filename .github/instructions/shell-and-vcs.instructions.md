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

- This project has no VCS yet. When one is added, update this file.
- **Never commit** the `venv/`, `temp/`, or `.pycache/` directories.
