---
applyTo: "docs/**"
---

## Markdown Conventions

- Table separator dashes align to the column header width.
- Use tree notation (`├──`, `└──`, `│`) for all directory/file structure listings.
- **NEVER use `---` as a horizontal rule / section divider** — use blank lines between sections.
- **Always surround lists with blank lines** — add a blank line before the first list item and after the last when adjacent to other block content.
- **Always wrap code samples in triple-backtick fences**.

## AsciiDoc Conventions (docs/*.adoc)

- Use `= Title` for the document title (level 0).
- Use `== Section` (level 1), `=== Subsection` (level 2), etc.
- Use `[source,ini]`, `[source,python]`, etc. for code blocks.
- Cross-references: `<<anchor-id,Display Text>>`.
- Include files: `include::other.adoc[]`.
- Images: `image::path/to/image.png[Alt text]`.
- Admonitions: `NOTE:`, `TIP:`, `IMPORTANT:`, `WARNING:`, `CAUTION:`.

## Document Scope

- `docs/userguide.adoc` — end-user instructions: installing, running, using every feature.
- `docs/developerguide.adoc` — architecture, module map, plugin API, adding new features, build and release process.
