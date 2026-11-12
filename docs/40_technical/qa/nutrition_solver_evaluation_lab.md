# Nutrition Solver evaluation lab v1

Status: local pilot, not a release gate. Date: 2026-11-12.

## Ownership and scope

This lab belongs to Nutrition Solver. It imports the pure solver contracts and
optimizer; it does not import the AI Assistant evaluation lab, call a model, write
product entities, or treat an AI response as solver evidence.

The fixed fixture contains 157 operational food candidates captured from staging
on 2026-11-11. Its source is the separately integrated
`codex/solver-evaluation-30` branch, commit
`3fc6ce3b1102ceb1cb1b3aa7966cdbf83cd6bbc2`. The cases are the 30 synthetic
daily-plan requests from that evaluation. The fixture is a frozen evaluation input,
not today's production catalog or a nutritional authority. The implementation
starts from `origin/staging@3b569223d65da312e4bec3411cb157cf3b92cae9`;
the earlier branch was reviewed and integrated through an equivalent commit.

The lab currently exercises the raw-food CP-SAT daily-plan path. It reproduces
the current typed dietary/allergen filtering behavior and the target ranges used
by the operational adapter. It does not run persisted proposals, the primary
culinary-variant path, or a weekly program. It therefore cannot certify those
boundaries. A later version must add program fixtures and a culinary-variant
fixture after their staging and production catalogs are reconciled.

The frozen [baseline report](../../../nutrition_solver/evaluation_lab/baselines/2026-11-12/report.md)
found 26 feasible cases out of 30 (86.7%), below the initial 90% gate. Four
allergy-constrained cases failed: S16 and S22 were CP-SAT infeasible; S19 and
S21 lacked a required food-role group after filtering. No feasible result had
a measured hard-bound violation, and every infeasible result has a reason code.
The 26 feasible cases remain queued for culinary review. The reference run's
p95 calculation time was 4.56 seconds; this is solver time, not app latency.

## Run

From the repository root, with the project's Python dependencies installed:

```sh
python -m nutrition_solver.evaluation_lab --out /tmp/nutrition-solver-lab-v1
```

The output directory contains `run.json` (complete inputs, alternatives,
metrics and diagnostics), `report.md` (readable summary), and
`human_review_template.json`. The command is read-only. To inspect a small
subset quickly:

```sh
python -m nutrition_solver.evaluation_lab --out /tmp/solver-smoke --cases S02,S16 --alternatives 1 --time-limit-ms 200 --no-stability
```

For a candidate change, use the same fixture, case list, configuration and
environment; save the prior `run.json`, then add
`--compare /absolute/path/to/prior/run.json`. The comparison refuses a
different case fixture, catalog fixture or configuration. `run_id` and
`implementation_digest` identify code and inputs. Timing is measured with a
monotonic clock but varies by machine load; compare latency on the same runner
class and repeat runs before drawing a performance conclusion.
The comparison names new infeasibility, new hard violations, a nutrition-score
drop over five points, increased affinity mismatches, and a maximum-repetition
increase over one. These are review triggers, not a single blended score.

To score the culinary review, fill every 1–5 rating in
`human_review_template.json`, add reviewer and date, and rerun with
`--review /absolute/path/to/completed-review.json`. Keep the signed review
with the run, not in product data. The numeric review threshold is an initial
team gate, not a substitute for a qualified nutritional or safety decision.

## Cases and metrics

The 30 cases cover omnivore, vegetarian, vegan and pescatarian patterns; energy
and macro target variation; single and combined allergies; exclusions; food
preferences; low cooking time; and low budget. Five cases also probe a repeated
solve and a 1% energy-target change. Some cases intentionally expose current
failures. New boundary and impossible cases belong in later versioned suites.

| Dimension | Automatic evidence | Initial threshold | Human evidence |
|---|---|---|---|
| Feasibility | Solution count, expected outcome, reason code on failure | At least 90% feasible and every expected-feasible failure named | Decide whether a request itself is reasonable |
| Nutritional validity | Independent hard-bound check; daily kcal/protein/carbs/fat deviations | Zero hard violations; existing nutrition score at least 80 per feasible case | Review nutritional appropriateness beyond implemented rules |
| Culinary quality | Role grammar, meal affinity mismatches, raw/dry ingredient flags, presence of validated-recipe evidence | Flags must be visible; no automatic culinary approval in v1 | Coherence, preparation, portion realism, practicality, local relevance, each 1–5 |
| Variety | Distinct foods, maximum daily repetitions, concentration HHI, distinct alternatives and overlap | Report and compare; no universal pass threshold yet | Judge repetition across meals and days |
| Stability | Same-input selection signature and food overlap after +1% energy | Report; investigate changes rather than fail on a chosen overlap alone | Judge whether changes are perceptibly arbitrary |
| Time | Per-case wall time and suite p95 | p95 at most 6 seconds on the reference runner | Judge experienced wait in the app separately |
| Infeasibility | Machine reason and candidate count; zero unexplained failures | Every infeasible result has a nonempty reason | Judge whether the explanation is accurate and actionable |

The automatic gate fails for any new hard violation, unexplained failure, failed
expected-feasible case, nutrition score below 80, overall feasibility below 90%,
or p95 above six seconds. These are provisional thresholds. Record changes to
them with the baseline impact before using them for integration.

Human review requires all feasible cases, named reviewer and date, all five
dimensions scored 1–5, no score of 1–2, and mean score at least 4. The reviewer
must see the selected meal portions in `report.md` and the full alternatives in
`run.json`, not just aggregate metrics. The current
`role_grammar_score_existing` can be 100 for a culturally implausible meal;
it is deliberately not labeled culinary validity.

## Shared end-to-end checks

Only the three scenarios in
`nutrition_solver/evaluation_lab/fixtures/shared_e2e_cases_v1.json` cross into
the assistant's evaluation surface: ordinary daily plan, allergy-constrained
daily plan, and seven-day program. They are identifiers and attribution
criteria, not an import of the Assistant lab's dataset. Execute them through
the trusted proposal path after the solver-only run. Compare the normalized
request, catalog snapshot, solver diagnostics and final proposal:

1. If eligible data or validated variants are missing before solving, classify
   **catalog** and retain the exact missing capability.
2. If a valid input reaches the solver and it violates a hard rule, returns a
   false infeasibility or makes an unacceptable optimization tradeoff, classify
   **solver** with the pure-case reproduction.
3. If the solver result is valid but intent, targets, alternatives, explanation
   or pending-review status is lost, classify **assistant/orchestration**.
4. If the first failing boundary is unclear, mark **unattributed** and retain
   the trace; do not assign ownership from the visible symptom.

No user health data is needed. Use synthetic or approved de-identified inputs.

## Regression intake and integration decision

When a real failure is reported, save a synthetic or de-identified input,
catalog/solver/contract versions, expected invariant, observed proposal,
reason code, and first proven failing boundary. Add a minimal versioned case
that reproduces the defect, run it against the baseline, then compare a
candidate change over the entire suite. Never loosen an existing hard
constraint merely to make a case feasible. Link the case to the issue and
retain the old output as evidence, not as desired behavior.

An integration recommendation requires: identical-case comparison; no new
infeasible or hard-violation cases; automatic gate pass; completed human
review; explicit improvement and regression table; catalog freshness check;
and focused product-path checks for every affected Meal, DailyPlan or Program
flow. A run from this v1 alone **cannot** claim a program, culinary, clinical
or production improvement. Integration and publication follow the repository
CI policy and require Felipe's authorization for publication.
