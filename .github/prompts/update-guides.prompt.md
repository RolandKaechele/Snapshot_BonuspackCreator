---
description: "Sync docs/userguide, docs/developerguide, docs/plugin-developerguide, README.md, todo.md, and CHANGELOG.md with an already-made code change."
name: "Update Guides"
agent: "agent"
argument-hint: "Describe the code change already made that needs doc updates"
---

# Update Guides

Bring documentation up to date with a code change that has already been implemented (e.g. on this branch), per `.github/instructions/doc-sync.instructions.md`. Use this when the implementation is done but docs were not updated alongside it.

## How to Execute

- **Chat**: type `/update-guides` followed by a description of the change (or point at the diff/commit), then send.
- **Command Palette**: run `Chat: Run Prompt...` and select `Update Guides`.
- **Editor**: open this file and click the play (▶) button in the editor title bar.

## 1. Identify What Changed

- Inspect the relevant diff (`git diff`/`git status`) or ask the user for the changed files/behavior if not obvious.
- Classify the change: new/changed UI (menu, tab, dialog, workflow), new/changed module or architecture, new/changed `pack.ini`/JSON field, new test file, or plugin API change.

## 2. Update the Matching Guide

Per `.github/instructions/doc-sync.instructions.md`:

- UI/workflow change → relevant chapter under `docs/userguide/` (see chapter list: `03-main-window.adoc`, `04-pack-files.adoc`, `05-photos-tab.adoc`, `06-overwrite-texts-tab.adoc`, `07-city-events-tab.adoc`, `09-love-lens-tab.adoc`, `10-plugin-system.adoc`, etc.).
- Module/architecture change → `docs/developerguide/03-project-structure.adoc` and `04-architecture.adoc`.
- `pack.ini`/JSON schema change → `docs/developerguide/07-pack-json-schema.adoc`.
- New test file → `docs/developerguide/08-testing.adoc`.
- Plugin API change → `docs/plugin-developerguide/03-plugin-api.adoc` (and `04-pack-manager-access.adoc`/`05-ui-integration.adoc` if relevant).
- Follow `.github/instructions/documentation.instructions.md` formatting conventions (AsciiDoc section levels, cross-references, admonitions, no `---` dividers in Markdown).

## 3. Update README.md and todo.md

- `README.md`: update if setup, quick-start, or build/release steps changed.
- `todo.md`: check off/remove resolved "Improvements"/"Known Issues" entries; add new "Known Issues" or "Future" entries surfaced by the change.

## 4. Update CHANGELOG.md

- Add a one-line bullet for the change under `[Unreleased]`, in the matching `### Added`/`### Changed`/`### Fixed`/`### Removed` subsection (create it if missing).

## 5. State What Didn't Need Updating

- If a doc category has no applicable change, say so explicitly rather than skipping silently (e.g. "no plugin API changes, plugin-developerguide untouched").

## 6. Verification Pass

- Re-read every file you modified to confirm the edit applied correctly and formatting matches conventions.
- Summarize which docs were updated and why, and which were intentionally left untouched.

## Out of Scope

- Do not modify application source code — this prompt only touches `docs/**`, `README.md`, `todo.md`, and `CHANGELOG.md`. Use `/pr-execution` when code changes are still needed.
- Do not run `git commit`, `git push`, or `svn commit`.
