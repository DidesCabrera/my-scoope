# Decision 0148: shadow mode separates nutritional and functional quality

## Status

Accepted in NSO09.

## Decision

Backend comparison executes the active and shadow optimizers against the same immutable problem.
Only the active result is eligible for proposal generation. The comparison emits compact telemetry
for statuses, selected-food overlap, nutritional score delta, meal-grammar score delta and hard
regression reasons.

Quality has two visible axes: proximity to preferred nutritional ranges and coverage of required
functional role groups with valid component counts. Missing capability data stays a warning rather
than being inferred silently.

A shadow result is a hard regression when it becomes impossible after an active feasible result,
loses more than 15 nutritional-quality points, or loses more than 20 functional-quality points.

## Consequences

- CP-SAT can be evaluated without changing user-visible proposals.
- Rollout decisions rely on structured quality and regression data.
- Explanations can tell reviewers why a composition is coherent, not only list macro differences.
- Environment settings select active backend, shadow backend and bounded runtime.
