---
description: "List every workflow prompt available in .github/prompts and what each one is for."
name: "List Agents"
agent: "agent"
argument-hint: "Optional: no input needed"
---

# List Agents

Give an overview of every workflow prompt (agent) available in this repository under `.github/prompts/`.

## How to Execute

- **Chat**: type `/list-agents` and send.
- **Command Palette**: run `Chat: Run Prompt...` and select `List Agents`.
- **Editor**: open this file and click the play (▶) button in the editor title bar.

## 1. Scan for Prompts

- List all `*.prompt.md` files in `.github/prompts/` (re-scan live rather than relying only on the table below, since new prompts may have been added since this file was last updated).
- For each file, read its frontmatter `name`/`description` and its first section to summarize purpose, invocation slug, and scope (what it touches / what it explicitly avoids).

## 2. Current Prompts (as of this file's last update)

| Invoke | Name | Purpose |
| ------ | ---- | ------- |
| `/pr-execution` | PR Execution | Implement a requested change end-to-end, then update affected `docs/*_Analysis.md`, userguide/developerguide/plugin-developerguide, `README.md`, `todo.md`, and `CHANGELOG.md` before handoff for commit. |
| `/create-analysis-document` | Create Analysis Document | Research a subject (plugin model, LoRA, bonus pack source, asset format) and write/update its `docs/*_Analysis.md` writeup, grounded in verified facts. |
| `/update-guides` | Update Guides | Sync `docs/userguide`, `docs/developerguide`, `docs/plugin-developerguide`, `README.md`, `todo.md`, and `CHANGELOG.md` with a code change that was already implemented but not yet documented. |
| `/release-build` | Release Build | Verify prerequisites and run the `scons` release build per `README.md`; on success, roll `CHANGELOG.md`'s `[Unreleased]` section into a new dated version. |
| `/init-project` | Init Project | Bootstrap the dev environment: create/verify the venv via `cli.bat`, install dependencies, and confirm the app launches. |
| `/list-agents` | List Agents | This prompt — lists all available workflow prompts and their purpose. |

## 3. Report

- Present the table (refreshed with any newly discovered prompts not yet listed above).
- If a prompt file exists on disk but is missing from the table above, flag it and suggest this file be updated to include it.
- Briefly note which prompt to use for the kind of task the user is about to do, if that context is available from the conversation.

## Out of Scope

- Do not execute any of the listed prompts — this prompt only reports on what's available.
- Do not run `git commit`, `git push`, or `svn commit`.
