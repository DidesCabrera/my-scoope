# Docs Information Architecture

Status: current
Last updated: 2026-07-08

## Purpose

`docs/` must help My Scoope evolve faster, not compete for attention.

The folder is not a flat knowledge dump. It is an information system with numbered layers of authority, so a developer or AI can quickly understand what is current, what is planned, what was decided, what is operational and what is historical.

## Official structure

```text
docs/
  README.md
  00_current/
    AI_README.md
    PROJECT_STATE.md
    architecture/
    design/
    features/
  10_active_cycles/
  20_decisions/
  30_manuals/
  40_technical/
    operations/
    qa/
  90_archive/
```

## Layers of documentation

| Layer | Path | Role | Authority |
| --- | --- | --- | --- |
| AI entrypoint | `docs/00_current/AI_README.md` | First reading path for AI-assisted work | High |
| Current truth | `docs/00_current/` | Active architecture, product contracts, features and design | High |
| Active cycles | `docs/10_active_cycles/` | Future, active, paused, completed or superseded cycle plans | Medium until implemented |
| Decisions | `docs/20_decisions/` | Accepted decisions and technical history | High for rationale |
| Manuals | `docs/30_manuals/` | Official human-facing usage or operation manuals | Medium/high |
| Technical operations | `docs/40_technical/` | CI, QA, testing, exports and operational policies | High for technical workflow |
| Archive | `docs/90_archive/` | Historical or superseded context | Low |
| Personal notes | `manual_docs/` | Human private notes outside official docs | Not authoritative |

## Export-aware reading

`docs/40_technical/operations/export_for_chatgpt.md` defines how official documentation and source files are packaged for IA-assisted work.

Exports must preserve the same authority hierarchy as `docs/`:

- `planning` should include current docs, active cycles, decisions and export policy.
- focused modes should include only the documentation needed for their domain.
- `90_archive/` should remain excluded unless historical context is explicitly required.
- `manual_docs/` must remain outside official exports.

## Authority rules

1. Current code and tests are the executable truth.
2. `docs/00_current/` explains how the product and architecture should be implemented today.
3. `docs/40_technical/` explains how the system should be tested, exported, stabilized and operated.
4. `docs/20_decisions/` explains why durable choices were made.
5. `docs/10_active_cycles/` can guide upcoming work but does not override current contracts.
6. `docs/90_archive/` is historical context only.
7. `manual_docs/` must stay outside AI export and implementation decisions.

## Document status

Every new planning or decision document should declare a status near the top.

Recommended statuses:

```text
current
planned
active
paused
completed
superseded
accepted
draft
```

Use them consistently:

- `current`: vigente operational or architecture document.
- `planned`: cycle is prepared but not started.
- `active`: cycle is being implemented.
- `paused`: cycle is intentionally held.
- `completed`: cycle finished and may have closure decisions.
- `superseded`: document is replaced by a newer one.
- `accepted`: decision is adopted.
- `draft`: proposal not yet accepted.

## When to create a document

Create or update documentation when it prevents future ambiguity.

Good reasons:

- A new app boundary is created.
- A workflow or testing policy changes.
- A repeated bug leads to a durable rule.
- A future cycle is planned and needs stable scope.
- A decision has consequences for future patches.

Weak reasons:

- Temporary implementation notes.
- Duplicating code behavior line by line.
- Recording every conversation detail.
- Adding another roadmap with no status.

## Planning-to-decision flow

Use this flow for large changes:

1. Draft or update a cycle in `docs/10_active_cycles/`.
2. Implement patches in small steps.
3. Promote durable outcomes into `docs/00_current/`.
4. Register accepted rationale in `docs/20_decisions/`.
5. Move stable human-facing instructions into `docs/30_manuals/` when needed.
6. Keep technical policies in `docs/40_technical/`.
7. Archive or mark superseded content when it stops guiding work.

## AI reading behavior

An AI should not read all docs equally.

Expected flow:

1. Read `docs/00_current/AI_README.md`.
2. Read `docs/00_current/PROJECT_STATE.md` if present.
3. Read task-specific current docs.
4. Read task-specific technical docs when touching tests, CI, QA, exports or staging.
5. Read related decisions for rationale.
6. Read active cycle docs only if the task is about future work, active planning or a cycle patch.
7. Avoid archive unless the user asks for historical context.

## UI testing note

My Scoope should not accumulate fragile UI tests. UI should be tested automatically only as a minimal contract for navigation, permissions, rendering and critical actions.

Avoid tests that freeze CSS classes, exact HTML structure, decorative copy or component counts.

Prefer:

- page loads;
- expected redirect;
- permission boundary;
- critical form behavior;
- smoke render for important views.
