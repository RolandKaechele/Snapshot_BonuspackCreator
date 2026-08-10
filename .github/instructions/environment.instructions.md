---
applyTo: "**"
---

## Environment

- **Python**: 3.12, virtual environment at `./venv`
- **Run Python**: `venv\Scripts\python.exe` (Windows, not `python3` or `python`)
- **Package manager**: pip, dependencies in `requirements.txt`
- **Portable runtime**: `temp\Python_3.12.6_64bit\` — used only by `cli.bat` to bootstrap the venv; never import from it directly.

## Creating / Activating the Venv

Always use `cli.bat` to create and activate the venv. Do not call `python -m venv` manually.

## Key Dependencies

- `PyQt6` — all UI (widgets, signals, painting)
- `Pillow` — image loading and dimension validation
- `configparser` — reading and writing `pack.ini` files

## Pycache

- Set `PYTHONPYCACHEPREFIX=.pycache` in environment or `cli.bat` so all `__pycache__` output goes to one place and does not scatter across `src/`.
- To clean: `for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"`

## MCP / Tool Execution

- Prefer `venv\Scripts\python.exe` for all terminal Python commands.
- Never run bare `python` or `python3` in terminals; the system Python may differ.
