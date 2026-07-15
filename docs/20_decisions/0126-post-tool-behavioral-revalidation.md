# 0126 — Post-tool behavioral revalidation

Status: accepted
Date: 2026-07-14
Cycle: PT06

## Context

The post-tool transport now returns provider-written replies instead of a local
acknowledgement on healthy tool turns. Behavioral requirements that were hidden
or overwritten by that fallback must therefore be validated again against the
real provider.

The existing `known_facts_not_reasked` gate had one blind spot: it considered a
fact known only after finishing the turn. A profile read could populate weight,
height, age and sex, while the provider follow-up re-asked those same facts in
the same turn without failing the gate.

## Decision

- Treat facts present in the current turn's final brief snapshot as known before
  evaluating that turn's semantic missing slots.
- Add bounded, scenario-owned visible-question markers for known profile fields,
  so a provider cannot hide a redundant question behind correct semantic
  metadata.
- Add a targeted live scenario that reads the personal ficha and requires
  weight, height, age and sex to remain known without repetition.
- Re-run the ambiguous-message restraint scenario with the original product
  wording, `¿Qué está pasando?`, and require zero tool calls.

## Consequences

PT06 protects both the structured contract and the visible UX. A same-turn
profile read followed by a redundant intake question now blocks the release
gate. The marker list remains scoped to the scenario rather than becoming a
global deterministic language parser.
