# Decision 0196: capability-oriented workspace queries

Status: accepted
Date: 2026-09-16

## Context

AI Intake selected product read tools through lightweight lexical heuristics. A real
staging transcript showed the resulting architectural failure: the assistant could
read the active calendarization, but a following request to list programs in the
user's `libreria` did not receive `list_user_programs`. The provider therefore claimed
that the library was unavailable even though the capability and owner-scoped query
already existed.

Normalizing accents, plurals and common verb forms fixes known phrases but does not
make capability access reliable. Exposing every micro-tool on every turn avoids the
lexical gate, but materially enlarges the provider request and can collide with the
technical input-token guardrail.

## Decision

AI Intake receives one stable provider-facing read capability named
`query_workspace`. Its typed `resource` selects foods, meals, daily plans, programs,
calendarization, proposals or saved comparisons. Optional `object_id`, `search` and
`limit` arguments distinguish detail, search and list requests.

The product adapter translates that envelope into the existing read tools and queries.
Those implementations remain authoritative for authentication, ownership, visibility,
serialization and error mapping. `query_workspace` cannot write data and the executor
still enforces the read-only category and result limits.

The older read tools remain in the canonical registry for compatibility, direct
executors and MCP projections. They are not the default semantic routing surface for
AI Intake. Lexical heuristics may still set `tool_choice=required` for an unequivocal
operation or expose a specialized capability, but they no longer decide whether the
workspace read capability exists.

## Consequences

- Missing accents, plural forms and unanticipated natural phrasing cannot remove the
  assistant's ability to consult the user's nutrition library.
- The provider chooses a typed resource instead of choosing among many overlapping
  read micro-tools.
- The prompt stays bounded: one query schema replaces a large always-visible read
  catalog.
- The backend, not the model, retains authority over ownership and result limits.
- Real transcript failures become regression tests at both selection and adapter
  routing boundaries.
