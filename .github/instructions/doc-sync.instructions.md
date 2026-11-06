---
applyTo: "src/**"
---

## Keep Docs in Sync

Whenever a change adds, removes, or changes the behavior of a user-facing feature, menu item, tab, dialog, or module, update the matching documentation in the same change:

- New/changed menu items, tabs, dialogs, or workflows → relevant chapter under `docs/userguide/`.
- New/changed modules, their public functions, or architecture → `docs/developerguide/03-project-structure.adoc` and `04-architecture.adoc`.
- New/changed `pack.ini` fields or JSON schema → `docs/developerguide/07-pack-json-schema.adoc`.
- New/changed test files → `docs/developerguide/08-testing.adoc`.
- Plugin API changes → `docs/plugin-developerguide/`.

If a change has no user- or developer-facing effect (pure refactor, internal bugfix with no behavior change), docs do not need updating — but state that explicitly rather than skipping the check silently.
