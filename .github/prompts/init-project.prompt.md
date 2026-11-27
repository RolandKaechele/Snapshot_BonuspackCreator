---
description: "Bootstrap the dev environment: create/verify the venv via cli.bat, install dependencies, and confirm the app launches."
name: "Init Project"
agent: "agent"
argument-hint: "Optional: note anything unusual about the current setup"
---

# Init Project

Get a fresh or stale checkout into a working dev state, following `.github/instructions/environment.instructions.md`.

## How to Execute

- **Chat**: type `/init-project` and send (add notes if the setup is already partially done or behaving oddly).
- **Command Palette**: run `Chat: Run Prompt...` and select `Init Project`.
- **Editor**: open this file and click the play (▶) button in the editor title bar.

## 1. Check Current State

- Check whether `venv\` already exists and whether `venv\Scripts\python.exe` runs (`venv\Scripts\python.exe --version`).
- If `venv\` is missing or broken, proceed to bootstrap; if it's present and working, skip straight to verification.

## 2. Bootstrap the Venv

- Run `cli.bat` to create/activate the venv and install `requirements.txt` — never call `python -m venv` manually (see environment instructions).
- Do not import from `temp\Python_3.12.6_64bit\`; that portable runtime is only used by `cli.bat` to bootstrap the venv.

## 3. Verify Dependencies

- Confirm key dependencies are importable: `PyQt6`, `Pillow`, `configparser` (stdlib).
- Report the installed versions via `venv\Scripts\pip show <package>` if there's any doubt about the right version being picked up.

## 4. Verify the App Launches

- Run `venv\Scripts\python.exe src\main.py --debug` briefly to confirm the app starts without import/startup errors, then stop it (GUI apps won't exit on their own — treat this as a background/async check, not a sync one).
- Report any startup errors with full traceback rather than guessing at the cause.

## 5. Environment Hygiene

- Confirm `PYTHONPYCACHEPREFIX=.pycache` is set (env var or in `cli.bat`) so `__pycache__` output is centralized.
- Remind the user this project is a dual Git+SVN working copy — do not commit `venv/`, `temp/`, or `.pycache/`.

## 6. Report

- Summarize: venv state before/after, dependency versions verified, whether the app launched cleanly, and any manual step still needed (e.g. installing Ruby/7-Zip for release builds — see `/release-build`).

## Out of Scope

- Do not run the release build (`scons`) — use `/release-build` for that.
- Do not run `git commit`, `git push`, or `svn commit`.
