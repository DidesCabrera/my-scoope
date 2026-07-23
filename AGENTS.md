# My Scoope agent instructions

## Human Knowledge Center boundary

`admin_knowledge/` and `docs/00_current/features/admin_knowledge/` exist only to
present human-oriented explanatory material in the staff Knowledge Center.

- They are not a source of truth for product behavior, architecture, data
  contracts, permissions, or feature requirements.
- Do not use their wording to infer how the code works. Inspect implementation,
  migrations, tests, authoritative decisions, and the applicable current feature
  documentation instead.
- Do not update, synchronize, regenerate, or expand the Knowledge Center during a
  feature, refactor, bug fix, documentation cycle, or release by default.
- Change the Knowledge Center only when Felipe explicitly requests a Knowledge
  Center update in the current task.
- Product code must not import `admin_knowledge`. The only allowed integration
  points are Django installation/URL wiring and human navigation links.
- A feature is complete without a Knowledge Center change unless Felipe explicitly
  includes that app in scope.

These rules intentionally keep the human presentation layer from becoming a
second authority or influencing Codex's understanding of the codebase.
