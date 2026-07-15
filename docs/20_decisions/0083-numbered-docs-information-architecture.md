# 0083 - Numbered Docs Information Architecture

Status: accepted
Date: 2026-07-08

## Context

Decision 0082 established that My Scoope documentation should stop behaving like a flat folder and should instead guide AI-assisted work through authority layers.

After applying the first baseline, the folder names still remained too generic (`current`, `planning`, `decisions`, `archive`). This made the structure less immediately legible than intended and weakened the attention hierarchy for AI readers.

The project needs a more explicit structure where folder names communicate both order and purpose.

## Decision

Refactor the official documentation structure to numbered folders:

```text
docs/
  README.md
  00_current/
  10_active_cycles/
  20_decisions/
  30_manuals/
  40_technical/
  90_archive/
```

Use these responsibilities:

- `00_current/`: current source of truth for architecture, product contracts, features and design.
- `10_active_cycles/`: planned, active, paused, completed or superseded cycles.
- `20_decisions/`: accepted decision records and technical history.
- `30_manuals/`: official human-facing manuals.
- `40_technical/`: operational technical policies, QA, CI, testing and export documentation.
- `90_archive/`: historical or superseded context.

Keep `docs/` lowercase to match the existing repository convention and avoid case-sensitivity problems across macOS, GitHub and Linux environments.

## Consequences

The AI entrypoint is now:

```text
docs/00_current/AI_README.md
```

The current project state is now:

```text
docs/00_current/PROJECT_STATE.md
```

The docs information architecture policy is now:

```text
docs/40_technical/operations/docs_information_architecture.md
```

Planning references move from `docs/planning/` to `docs/10_active_cycles/`.

Decision references move from `docs/decisions/` to `docs/20_decisions/`.

Archive references move from `docs/archive/` to `docs/90_archive/`.

Testing and QA references move from `docs/current/qa/` to `docs/40_technical/qa/` because they guide technical workflow rather than product truth.

Operational export and CI policy references move from `docs/current/operations/` to `docs/40_technical/operations/` for the same reason.

## Compatibility note

This is a documentation-only refactor, but scripts that export docs for AI must be updated with the new paths so focused ZIP exports continue to include the correct context.
