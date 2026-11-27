---
description: "Execute a PR-ready change: implement the request, then update every affected analysis doc, guide, README.md, and todo.md before handing off for commit."
name: "PR Execution"
agent: "agent"
argument-hint: "Describe the change/feature/fix to implement"
---

# PR Execution

Implement the requested change end-to-end and leave the repository in a PR-ready state: code correct, tests passing, and **all** affected documentation updated in the same pass. Follow the priority order from `.github/copilot-instructions.md`: **1. Correctness → 2. Tests → 3. Docs → 4. Requirements → 5. Packaging.**

## How to Execute

- **Chat**: type `/pr-execution` in the chat input, followed by a description of the change/feature/fix to implement, then send.
- **Command Palette**: run `Chat: Run Prompt...` and select `PR Execution`.
- **Editor**: open this file and click the play (▶) button in the editor title bar.

Provide the task description as the prompt argument (what `${input}` maps to); without one, state the intended change in the chat message before invoking the steps below.

## 1. Implement

- Make the requested code change, following `.github/instructions/coding-conventions.instructions.md` and `.github/instructions/environment.instructions.md`.
- Modify only the functions/classes/modules directly required for the change.
- Run/add tests per `.github/instructions/testing.instructions.md` (`venv\Scripts\pytest`) and make sure they pass.

## 2. Update Analysis Documents (`docs/*_Analysis.md`)

- If the change touches a bonus pack source, plugin model/LoRA, asset pipeline, or anything already documented in an existing `docs/*_Analysis.md` file, update that file to reflect the new behavior/findings.
- If the change introduces a genuinely new analyzable subject (new plugin, new bonus pack source, new model) with no existing analysis doc, create one following the naming pattern `docs/<Subject>_Analysis.md` and the conventions in `.github/instructions/documentation.instructions.md`.
- Skip this step explicitly (state it, don't silently omit) if the change has no analysis-relevant surface.

## 3. Update Guides

Apply `.github/instructions/doc-sync.instructions.md`:

- New/changed menu items, tabs, dialogs, or user workflows → relevant chapter under `docs/userguide/`.
- New/changed modules, their public functions, or architecture → `docs/developerguide/03-project-structure.adoc` and `04-architecture.adoc`.
- New/changed `pack.ini` fields or JSON schema → `docs/developerguide/07-pack-json-schema.adoc`.
- New/changed test files → `docs/developerguide/08-testing.adoc`.
- Plugin API changes → `docs/plugin-developerguide/`.
- Follow Markdown/AsciiDoc conventions in `.github/instructions/documentation.instructions.md` (tree notation for directory listings, no `---` dividers, blank lines around lists, fenced code blocks).
- If the change has no user- or developer-facing effect (pure refactor, internal bugfix with no behavior change), state explicitly that guide updates are not needed rather than skipping silently.

## 4. Update `README.md`

- Reflect any change to setup steps, quick-start instructions, build/release process, or supported games/features.
- Keep edits minimal and consistent with the existing structure and tone.

## 5. Update `todo.md`

- Remove/check off any "Improvements" or "Known Issues" entry that this change resolves.
- Add a new entry under "Known Issues" if the change surfaces a new limitation.
- Add a new entry under "Future" if follow-up work was identified but intentionally deferred.
- Leave entries unrelated to this change untouched.

## 6. Update `CHANGELOG.md`

- Add a bullet describing the change under the `[Unreleased]` section, in the matching `### Added`/`### Changed`/`### Fixed`/`### Removed` subsection (create the subsection if it doesn't exist yet).
- Keep entries user-facing and concise — one line per change, matching the phrasing style of existing entries.

## 7. Verification Pass

After all edits:

- Re-read every file you modified or created to confirm changes applied correctly (see "Edit Verification" in `.github/instructions/coding-conventions.instructions.md`).
- Use `get_errors` on changed source files.
- Summarize: what was implemented, which docs/guides/README/todo/CHANGELOG were updated (or explicitly why not), and any manual follow-up the user should do (e.g. running the build, committing).

## Out of Scope

- Do not run `git commit`, `git push`, or `svn commit` — stop after edits and suggest a commit message per `.github/instructions/shell-and-vcs.instructions.md`.
- Do not open or submit the actual pull request unless explicitly asked.
