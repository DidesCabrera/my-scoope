# Export workspace contracts

Cycle-aware export modes declare an intentional workspace rather than an
accidental subset of the repository. Each mode has:

- a workspace type and purpose;
- a documented fallback;
- a generated `EXPORT_MANIFEST.md`;
- an optional executable validation profile.

`ai_behavior` is the first migrated cycle workspace. New cycles should declare
their primary mode and validation boundary before implementation patches begin.
