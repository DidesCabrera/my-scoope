# Decision 0197: canonical library projections and capability catalog gate

Status: accepted
Date: 2026-09-17

## Context

The assistant could execute library tools yet return facts that disagreed with the
web product. Separate queries counted drafts, embedded snapshots and program-derived
objects, while a provider sanitizer silently reduced collections to eight items.
The existence of a registered capability therefore overstated real user coverage.

The living request catalog also needed a way to evolve from incidents without becoming
documentation that could drift independently of code and real model behavior.

## Decision

Foods, Meals, DailyPlans and Programs use shared canonical user-library querysets in
both web list pages and assistant workspace reads. Collection results expose exact
totals and explicit offset pagination metadata. Provider context may preserve the
executor's bounded page but may not silently apply a smaller second limit.

The request catalog is an executable product contract. A focused gate validates its
structured rows and the high-value read, patch, routing and solver behaviors; the row
count evolves when a later decision adds genuinely different product outcomes.
Real-provider validation includes an opt-in `bibliotecas_coherentes` scenario that
derives expected totals from the selected user's canonical queries and compares those
facts with the model's visible answers.

Coverage labels remain intentionally honest. Tool registration alone is insufficient:
end-to-end resolution, authorization, preview or proposal semantics, and coherent
visible output are required before a request is marked covered.

## Consequences

- Assistant and web library counts cannot diverge because of separate visibility
  definitions.
- Truncation is explicit and follow-up pages are addressable.
- Real staging incidents can become catalog rows plus reproducible regressions.
- Live model validation remains opt-in because it consumes provider usage and depends
  on external configuration.
- High-risk and specialized mutations stay outside the generic patch until their own
  domain adapters and review policy exist.
