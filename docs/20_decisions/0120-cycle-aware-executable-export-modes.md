# 0120 — Cycle-aware executable export modes

Status: accepted
Date: 2026-07-14

## Decision

My Scoope export modes are executable architectural workspaces, not only file
filters. A mode intended for implementation must declare its purpose, fallback
and validation boundary, and should prove that boundary from the generated
workspace.

`ai_behavior` is the first reference implementation. Existing modes remain
compatible and will be migrated when their next active cycle requires work.

## Consequences

- The ZIP expected for each patch can be recorded when a cycle is created.
- Missing dependencies are detected during export generation instead of after
  sharing the archive.
- `full` remains the recovery and broad-regression artifact, not the default.
- Architecture changes may require updating affected export contracts.
