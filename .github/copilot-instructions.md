# GitHub Copilot Instructions

## General Interaction Rules

- When clarification is needed before proceeding, ask questions using a **multiple-choice format** with numbered or lettered options and always include a freetext escape option (e.g. "Other — please describe") so the answer is never restricted to predefined choices.

## Project Overview

**Snapshot Pack Creator** — a Windows desktop application for creating and editing bonus content packs for the games *Snapshot!* and *Snapshot: Lewd Shores*. Built with Python 3.12, PyQt6, and a QSS stylesheet. Runs fully offline. Entry point: `src/main.py`.

## Task Priority Order

When a task spans multiple domains, apply rules in this order: **1. Correctness → 2. Tests → 3. Docs → 4. Requirements → 5. Packaging.** Use the PR checklist sub-chapters as named checklists.

## Project Structure

```
├── src/                main application source
│   ├── main.py         entry point
│   ├── app_debug.py    central debug flag module
│   ├── ui/             main window, menubar, statusbar, stylesheet
│   └── modules/        one Python module per feature
├── plugins/            user-installable plugin packages
├── docs/               Analysis.md, userguide.adoc, developerguide.adoc
├── tests/              pytest test files
└── temp/               portable Python runtime (never committed)
```

- **`requirements.txt`** — pinned pip dependencies at root; updated when adding packages.
- **`cli.bat`** — creates/activates the venv and installs requirements; run it first.

> Detailed rules are organised into topic instruction files in `.github/instructions/`.
> VS Code Copilot loads them automatically based on their `applyTo` patterns.
>
> | File | Scope | Topics |
> | ---- | ----- | ------ |
> | `environment.instructions.md` | always | Python env, venv, dependencies, pycache |
> | `shell-and-vcs.instructions.md` | always | Shell rules, batch scripts, encoding |
> | `coding-conventions.instructions.md` | always | Python style, PyQt6 rules, debug output |
> | `testing.instructions.md` | `tests/**` | pytest, fixtures, coverage |
> | `documentation.instructions.md` | `docs/**` | Markdown/AsciiDoc rules |
