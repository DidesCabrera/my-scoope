# EXP02 — Cycle-aware executable export modes

Status: active
Date: 2026-07-14
Owner: Architecture / Developer Experience
Primary implementation: `scripts/export_for_chatgpt.sh`
Reference workspace: `ai_behavior`

## Problem

Choosing an export ZIP was repeatedly decided during each development cycle.
When a focused mode missed a bootstrap or test dependency, the safe fallback was
to share `full`, increasing noise and delaying diagnosis.

## Decision

Exports are treated as architecture-aware workspaces. Every migrated mode must
declare:

1. workspace type and purpose;
2. primary development boundary;
3. fallback mode;
4. generated manifest;
5. executable validation profile when the mode is intended for code changes.

The export is sufficient only when its declared validation boundary runs from
the exported directory itself.

## Implementation stages

### EXP02-A — Common workspace contract — completed

- Add workspace metadata, fallback and validation profile lookup.
- Generate `EXPORT_MANIFEST.md` inside every ZIP.
- Support `--validate`, `--no-validate` and `EXPORT_VALIDATE`.
- Keep legacy modes compatible while they are migrated progressively.

### EXP02-B — `ai_behavior` executable reference — completed

- Add focused Django settings and URLConf for export validation.
- Keep real behavioral models and services.
- Remove unrelated dashboards, global onboarding middleware and product URL
  wiring from the smoke boundary.
- Declare compile, Django check and focused tests as the executable contract.

### EXP02-C — Progressive mode migration — planned

- Migrate active domain modes when a cycle next depends on them.
- Prefer shared architectural bundles over duplicated path lists.
- Add validation profiles proportionate to each mode's purpose.

### EXP02-D — Cycle template integration — planned

Every new cycle document should state:

- primary export mode;
- fallback mode;
- required validation;
- patch-by-patch artifact expectations.

## Operating rule

Use the focused cycle/domain mode for normal patches. Use `full` for export
construction, missing-dependency diagnosis, cross-domain architecture changes
and final regression at major cycle boundaries.
