# Decision 0147: optimize the day globally and expose distinct alternatives

## Status

Accepted in NSO08.

## Decision

CP-SAT uses one model for all meal slots. Per-meal ranges remain enforced while daily nutrient
ranges and hard repetition limits operate across slots. The solver can request up to ten ranked
alternatives by adding a no-good constraint after each selected-food composition.

Alternatives differ in selected food composition, not merely in opaque solver metadata. They keep
the same hard constraints and are returned through a separate serializable portfolio contract.

## Consequences

- A locally plausible meal can be adjusted in service of the whole-day ranges.
- Repetition is controlled across the plan rather than independently per meal.
- Consumers can present reviewable options without asking an LLM to invent substitutions.
- If no further feasible composition exists, the portfolio stops without relaxing constraints.
