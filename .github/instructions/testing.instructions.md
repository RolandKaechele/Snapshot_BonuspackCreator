---
applyTo: "tests/**"
---

## Testing

- Test runner: `pytest`, executed via `venv\Scripts\pytest`.
- Test files live in `tests/` and are named `test_<module>.py`.
- Each feature module in `src/modules/` should have a corresponding test file.
- Use `pytest-qt` for PyQt6 widget tests; access the `qtbot` fixture for signal/event testing.
- Isolate file-system tests using `tmp_path` (pytest built-in).
- Do not write tests that depend on external files at absolute paths — use fixtures to create temporary data.
