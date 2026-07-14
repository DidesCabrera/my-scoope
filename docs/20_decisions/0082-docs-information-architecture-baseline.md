# 0082 - Docs Information Architecture Baseline

Status: accepted, amended by 0083
Date: 2026-07-08

## Context

My Scoope now has enough documentation that adding more files without hierarchy can reduce efficiency.

The documentation has high value because it preserves architectural decisions, product intent, testing policy, app boundaries, planning cycles and operational lessons. However, for AI-assisted development, too much unranked documentation can compete for attention and create ambiguity.

The project needs a way to distinguish:

- current implementation truth;
- accepted rationale;
- future planning;
- historical context;
- personal notes that should not guide implementation.

## Decision

Adopt a documentation information architecture baseline.

The official reading hierarchy is:

1. Current source code and executable tests.
2. `docs/00_current/` as the current implementation contract.
3. `docs/20_decisions/` as accepted rationale and technical history.
4. `docs/10_active_cycles/` as strategic cycle planning.
5. `docs/90_archive/` as historical or superseded material.
6. `manual_docs/` as personal human notes outside official implementation context.

Add an AI entrypoint:

```text
docs/00_current/AI_README.md
```

Add an operational policy:

```text
docs/40_technical/operations/docs_information_architecture.md
```

Add a consolidated current-state document:

```text
docs/00_current/PROJECT_STATE.md
```

## Consequences

Future AI-assisted patches should start from `AI_README.md` instead of reading `docs/` as a flat folder.

New documentation should clearly answer one of these questions:

- What is true now?
- What decision was accepted and why?
- What cycle is planned, active, paused, completed or superseded?
- What historical context explains a current constraint?

Planning documents do not override current contracts until their outcomes are reflected in `docs/00_current/`, `docs/20_decisions/` or code.

Documentation work should prefer small patches:

- information architecture;
- current-state consolidation;
- decision records;
- planning updates;
- archive/supersession cleanup.

This decision also reinforces the current testing posture: avoid brittle UI tests that freeze CSS classes, exact HTML structure or decorative copy. UI automation should remain focused on smoke/render/permissions and critical flows.

## Follow-up opportunities

- Add explicit status headers to older planning documents that do not yet have them.
- Add an archive index if historical documentation grows.
- Periodically refresh `PROJECT_STATE.md` after major cycles close.
- Convert durable outcomes from completed planning cycles into concise current docs or decisions.

## Amendment

Decision 0083 refines this baseline by moving the generic folder names to explicit numbered folders. The intent of this decision remains valid; 0083 defines the current concrete folder layout.
