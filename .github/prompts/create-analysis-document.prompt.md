---
description: "Research a subject (plugin model, LoRA, bonus pack source, asset format) and write/update its docs/*_Analysis.md writeup."
name: "Create Analysis Document"
agent: "agent"
argument-hint: "Subject to analyze (plugin, model, bonus pack source, asset format) and what's already known"
---

# Create Analysis Document

Produce or update a `docs/<Subject>_Analysis.md` writeup for the given subject, grounded in verified facts from the codebase/files/web rather than assumptions.

## How to Execute

- **Chat**: type `/create-analysis-document` followed by the subject and any known context, then send.
- **Command Palette**: run `Chat: Run Prompt...` and select `Create Analysis Document`.
- **Editor**: open this file and click the play (▶) button in the editor title bar.

## 1. Check for an Existing Document

- Search `docs/*_Analysis.md` for a file already covering the subject (e.g. a plugin, model, LoRA, or bonus pack source). Reuse and update it rather than duplicating.
- If related analyses exist (e.g. a base model vs. a LoRA built on it), cross-link them instead of repeating content — follow the cross-reference style already used (`see [OtherAnalysis.md](OtherAnalysis.md)`).

## 2. Gather Facts

- Inspect the relevant source: `plugins/<name>/__init__.py`, `plugins/<name>/README.md`, `src/modules/`, `pack.ini`/JSON schemas, or any referenced model/checkpoint files.
- For external models/architectures, use web fetch to confirm details from primary sources (Hugging Face model cards, upstream repos) — do not guess architecture or licensing.
- Distinguish clearly between what is **validated** (tested end-to-end, e.g. on real hardware) and what is **implemented but unverified** or **assumed**. Call out corrections made during investigation (wrong assumptions found and fixed), as existing analysis docs do.

## 3. Write the Document

Follow the conventions in `.github/instructions/documentation.instructions.md` and the structure of existing `docs/*_Analysis.md` files:

- Title: `# <Subject> — Analysis` or `# <Subject> Plugin — Analysis (\`plugins/<name>\`)` for plugins.
- Include the standard disclaimer line: "The App is **not officially associated with Snapshot! or Tiny Secret Games**." for any game-related subject.
- Sections typically include: `## Source` (links/paths), `## Status` (validated/unvalidated, version), implementation details, and any corrections/gotchas discovered.
- Use fenced code blocks for code/config snippets, tree notation for directory listings, no `---` dividers, blank lines around lists.

## 4. Cross-Link and Register

- Add cross-references from/to related analysis docs where relevant.
- If the subject is a plugin or bonus pack feature already tracked in `docs/BonusContentTable.md` or `docs/ArchiveFeatureComparison.md`, update those tables too.
- If this analysis motivates follow-up implementation work, add an entry under `todo.md`'s "Future" section.

## 5. Verification Pass

- Re-read the created/updated file to confirm formatting and that no placeholder text remains.
- Summarize what was analyzed, what's validated vs. assumed, and any cross-links/table updates made.

## Out of Scope

- Do not implement the feature/plugin itself — this prompt only produces the analysis document. Use `/pr-execution` for implementation work.
- Do not run `git commit`, `git push`, or `svn commit`.
