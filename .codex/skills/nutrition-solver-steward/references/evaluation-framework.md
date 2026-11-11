# Solver evaluation framework

Use a stable scenario suite to distinguish genuine improvement from a result that
only looks better in one example. Begin with the smallest set that represents the
current product promise and expand it when real failures reveal a new class.

## Scenario record

Record:

- scenario ID, purpose, target user archetype, and planning horizon;
- synthetic or permitted input snapshot and catalog version;
- energy and nutrient targets, preferences, exclusions, availability, and budget
  or preparation constraints when applicable;
- hard constraints, soft preferences, objective weights, tolerances, and relaxation
  policy;
- solver, rule, and contract versions;
- expected invariants and known acceptable variation;
- output, metrics, human-review notes, and failure classification.

Include feasible, boundary, infeasible, sparse-catalog, and conflicting-preference
cases. Add regressions from observed failures after removing unnecessary personal
information.

## Quality dimensions

Evaluate only dimensions relevant to the scenario, but do not reduce quality to
macro distance alone:

- feasibility and explicit constraint violations;
- energy, macro, and applicable nutrient deviation;
- portion realism and allowed scaling;
- meal and day coherence;
- variety, repetition, and concentration in a small set of foods;
- preference, exclusion, and dietary-rule adherence;
- catalog availability, evidence confidence, and solver eligibility;
- practicality, preparation burden, cost, and local relevance when represented;
- stability under small input changes;
- explanation of infeasibility, relaxation, or substitution;
- latency and operational reliability when they affect the experience.

Quantitative scores support comparison; they do not replace review of realism and
user usefulness. Define the direction, scale, and acceptance threshold for every
metric before using a composite score.

## Failure classification

Classify the first proven failing boundary:

| Class | Typical evidence | Primary handoff |
|---|---|---|
| Catalog data | Missing, incorrect, ambiguous, or ineligible candidate data | Catalog Curation Steward |
| Contract | Producer and consumer disagree on meaning, units, missing states, or version | Catalog + Solver + Architecture |
| Optimization model | Objective, constraints, weights, tolerances, or relaxation produce poor tradeoffs | Nutrition Solver Steward |
| Implementation | Accepted model is implemented incorrectly or inconsistently | Backend specialist |
| Product policy | Desired behavior or user control is unresolved | Strategic Product Advisor / Felipe |
| Domain rule | Nutritional validity or safety criterion is uncertain | Qualified reviewer / Felipe |

Do not assign ownership from symptoms alone. A repetitive plan may come from a
small eligible catalog, an excessive diversity penalty, a broken filter, or an
accepted product constraint.

## Change gate

Before recommending adoption, compare the candidate with the baseline across the
relevant suite. Report improved, unchanged, and regressed scenarios; explain any
new infeasible cases; verify that constraints and relaxations remain visible; and
define rollback. A candidate is not ready when it improves averages by hiding a
material violation or damaging a priority scenario.
