# 0079 · Layer strictness by app tier

Date: 2026-07-06
Status: accepted

## Context

ADR [0001](0001-layer-boundaries.md) and `docs/00_current/architecture/rules.md` define a
strict `domain -> application -> presentation -> interface` split and describe it as
project-wide.

In practice, only `notas` and `ai_assistant` follow the full split today.
`nutrition_solver` follows it partially (`domain` + `application`, no `presentation`/
`interface` split yet). `food_catalog` uses `application/` + `infrastructure/`,
`admin_analytics` uses `selectors/` + `services/`, `accounts` uses `services/`, and
`admin_operations`/`core` have no layer split at all.

The architecture test that enforces the boundary
(`notas/tests/test_bounded_contexts.py`) only walks `notas/application`. It gives no
protection to the other apps, so the "no negociable" framing in `CLAUDE.md` was
misleading: it read as a project-wide guarantee that does not exist in code or in
tests.

Forcing the full split onto apps that are mostly read-oriented internal
dashboards (`admin_analytics`, `admin_operations`) or thin CRUD (`accounts`, `core`)
adds indirection without a matching benefit, since those apps don't need their write
logic reused across API/MCP/mobile entry points the way `notas` and `ai_assistant` do.

## Decision

Layer strictness is now explicitly tiered by app, instead of uniform:

**Tier 1 — strict layering required (`domain` → `application` → `presentation` →
`interface`):**

- `notas`
- `ai_assistant`
- `nutrition_solver`

These apps expose write logic that is or will be reused from multiple entry points
(web, API, MCP, internal AI). The existing rules in ADR 0001 and
`docs/00_current/architecture/rules.md` keep applying here without change, and
`notas/tests/test_bounded_contexts.py` keeps being the enforcement mechanism for
`notas`.

**Tier 2 — lightweight pattern allowed (`services`/`selectors`, no mandatory
`domain`/`presentation`/`interface` split):**

- `food_catalog`
- `admin_analytics`
- `admin_operations`
- `accounts`
- `core`

These apps do not need to adopt the four-layer split. What still applies to them,
without exception:

- Writes must be isolated in an identifiable services/commands module — never inline
  in a view or template-facing selector.
- Read-building code (selectors, viewmodels, page builders) must never write to the
  database.
- `application`-equivalent code must not depend on `request`, `messages`, `redirect`,
  or templates.

If a Tier 2 app later grows write logic that needs to be reused from another entry
point (API, MCP, mobile), promote it to Tier 1 as its own follow-up decision — do not
silently let the split creep in without documenting the move.

## Consequences

- `CLAUDE.md`'s "Reglas de arquitectura" section is updated to reference this tiering
  instead of presenting the four-layer split as universally non-negotiable.
- `docs/00_current/architecture/rules.md` gets a section distinguishing intentional
  Tier 2 simplicity from legacy gaps still to be fixed in Tier 1 apps (the existing
  "Known Current Gaps" section keeps meaning "not yet compliant", not "intentionally
  simple").
- No code changes required: this documents the architecture that already exists in
  the repo.
- Future PRs adding domain/presentation/interface folders to a Tier 2 app without a
  stated reason (reuse across entry points) should be questioned.