---
description: "Verify prerequisites and build a release via scons, following README.md's build steps."
name: "Release Build"
agent: "agent"
argument-hint: "Optional: specific build concern or target to check first"
---

# Release Build

Walk through producing a release build as documented in `README.md`'s "Building a Release" section, verifying prerequisites before invoking the build.

## How to Execute

- **Chat**: type `/release-build` and send (add notes if a specific concern should be checked first).
- **Command Palette**: run `Chat: Run Prompt...` and select `Release Build`.
- **Editor**: open this file and click the play (▶) button in the editor title bar.

## 1. Verify Prerequisites

Per `README.md` and `.github/instructions/environment.instructions.md`:

- Confirm `venv\Scripts\python.exe` exists (environment created via `cli.bat`, never `python -m venv` directly).
- Confirm `asciidoctor-pdf` is available (Ruby gem) for PDF documentation generation.
- Confirm `7zCon.sfx` is placed next to `7z.exe` for the SFX installer.
- Confirm `pyinstaller` is installed in the venv (`venv\Scripts\pip show pyinstaller`).
- If any prerequisite is missing, report exactly which one and the command to fix it from `README.md` — do not silently skip the build.

## 2. Run the Build

- Execute `venv\Scripts\python.exe -m scons` via the terminal tool.
- Use `venv\Scripts\python.exe` exclusively; never bare `python`/`python3` (see environment instructions).

## 3. Check the Result

- Confirm the build completed without errors; if it failed, report the failing step and relevant error output rather than retrying blindly.
- Check `build/` for expected output artifacts (spec file output, docs).

## 4. Update CHANGELOG.md

- Only on a **successful** build. Read `src/_version.py` for the new `BUILD_VERSION` (e.g. `v2026-11-27`).
- In `CHANGELOG.md`, rename the `## [Unreleased]` section to `## [<date from BUILD_VERSION, e.g. 2026-11-27>]`, keeping all its entries as-is.
- Add a fresh, empty `## [Unreleased]` section above it.
- If `[Unreleased]` already has no entries, skip this step and state so explicitly rather than creating an empty dated section.

## 5. Report

- Summarize prerequisite check results, the build command run, and outcome (success/failure with details).
- Report whether `CHANGELOG.md` was updated with a new version section.
- If docs (`docs/developerguide/09-build-and-release.adoc`) are out of sync with the actual steps taken, flag it — use `/update-guides` to fix.

## Out of Scope

- Do not install missing prerequisites that require elevated/interactive install prompts (e.g. installing Ruby or 7-Zip itself) — report what's missing and let the user install it.
- Do not run `git commit`, `git push`, or `svn commit`.
