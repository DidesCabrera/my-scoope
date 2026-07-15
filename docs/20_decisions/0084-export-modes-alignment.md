# 0084 - Export Modes Alignment

Status: accepted
Date: 2026-07-08

## Context

My Scoope now uses a numbered documentation architecture:

```text
docs/
  00_current/
  10_active_cycles/
  20_decisions/
  30_manuals/
  40_technical/
  90_archive/
```

The script `scripts/export_for_chatgpt.sh` is part of the AI-assisted development workflow. It determines what context an AI receives, which means it directly affects quality, speed and risk.

After reorganizing `docs/`, the project needed to document the export modes as an operational policy, not just keep them as shell logic.

## Decision

Treat `scripts/export_for_chatgpt.sh` as an official technical workflow.

Document its modes in:

```text
docs/40_technical/operations/export_for_chatgpt.md
```

Keep the current modes:

```text
ai
full
usda
foodcatalog
planning
adminanalytics
adminoperations
```

Add a help path to the script:

```bash
./scripts/export_for_chatgpt.sh --help
```

Use `planning` as the preferred mode for documentation, strategy, decisions and future cycles.

Use `ai` for general development context when tests and heavy datasets are not needed.

Use `full` when the task touches tests, CI, regressions, auth, security, credits, limits, proposals, AI Assistant production behavior or other critical logic.

Use focused modes only when their domain boundary is clear enough to reduce noise without hiding necessary context.

## Consequences

The export system becomes part of My Scoope's AI collaboration architecture.

Future modes should not be added casually. A new mode must reduce noise, map to a stable boundary and be documented.

The `planning` export must remain aligned with the numbered docs architecture and should not include `90_archive/` by default.

`manual_docs/` remains excluded from official exports because it contains personal notes, not project contracts.

## Validation

The shell script should pass:

```bash
bash -n scripts/export_for_chatgpt.sh
./scripts/export_for_chatgpt.sh --help
```

Documentation-only changes can be validated with:

```bash
git diff --check
```
