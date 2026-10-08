# Culinary-First Solver Cycle

Status: repository implementation complete; production fail-closed activation gated by catalog readiness
Date: 2026-10-07
Cycle: CFS00-CFS08

## Objective

Adopt validated culinary meals as the primary planning unit for standalone meals,
daily plans, onboarding and weekly programs. Raw-food composition remains a measured,
explicit transition fallback until the production culinary catalog satisfies the
coverage and human-review gate in Decision 0204.

## Invariants

- Nutrition targets do not override culinary identity, preparation or approved ratios.
- A culinary result contains only ingredients authorized by its persisted variant.
- Fondo, ensalada and postre are separate courses inside one meal.
- Allergies and dietary patterns filter candidates before optimization.
- Every generated entity remains a pending `NutritionProposal` until human approval.
- Variant evidence and portions are revalidated immediately before apply.
- Raw-food fallback is recorded as fallback and can be disabled by configuration.
- Knowledge Center is outside this cycle.

## Controlled tasks

| Task | Deliverable | Status |
|---|---|---|
| CFS00 | Architecture decision, boundaries and rollout gates | complete |
| CFS01 | Starter catalog v2 with explicit courses and dessert fruit | complete |
| CFS02 | Pure CP-SAT culinary meal/day planner over validated variants | complete |
| CFS03 | Culinary-first DailyPlan and onboarding generation | complete |
| CFS04 | Culinary-first standalone Meal proposals | complete |
| CFS05 | Common evidence path for weekly programs | complete |
| CFS06 | Apply-time digest, ingredient, unit, bound and ratio revalidation | complete |
| CFS07 | Focused regression and behavior tests | complete locally |
| CFS08 | Staging catalog expansion, human review and fail-closed activation | operational gate pending |

## Runtime flow

```text
NutritionBrief / target
  -> readable validated CulinaryVariants
  -> filter pattern, allergens, exclusions and meal kind
  -> choose one variant per slot
  -> adjust only permitted ingredient portions
  -> validate daily targets
  -> persist proposal + culinary evidence
  -> human approval
  -> revalidate evidence
  -> apply entity
```

If catalog coverage or feasibility is insufficient and
`NUTRITION_CULINARY_RAW_FALLBACK_ENABLED=true`, the existing food-level optimizer may
run. The proposal records `raw_food_fallback_used=true` and the catalog reason. Setting
the flag to `false` converts the same condition into an explicit failure.

## Delivered behavior

- `CulinaryTemplate` components accept a course classification.
- Starter v2 adds dessert fruit to main-meal families and includes `Naranja cruda`
  when the operational catalog contains it.
- Daily planning selects complete variants across all meal slots in one model and
  adjusts their portions against daily kcal and macro targets.
- Standalone meal generation selects a complete compatible variant before portion
  optimization.
- Weekly programs with a typed specification retain their existing culinary planner;
  portfolio-based programs now also retain selection evidence when their daily menus
  originate from culinary variants.
- Meal, DailyPlan and Program apply paths reject stale culinary evidence.

## Validation evidence

Focused tests cover:

- culinary selection before portion adjustment;
- explicit dessert-course preservation;
- standalone meal and DailyPlan proposal creation/application;
- stale catalog evidence blocking apply;
- starter coverage across supported meal kinds;
- compatibility with existing culinary-program, meal-proposal and onboarding tests.

The complete integration gate remains intentionally deferred to the integration
boundary under the repository validation policy. CFS08 requires staging-owned catalog
and human-review evidence that local fixtures cannot supply.

## CFS08 checklist

1. Seed or import the starter v2 against the staging operational catalog.
2. Curate enough additional templates and variants to satisfy Decision 0204 coverage.
3. Complete human rubric review for at least one variant per active family.
4. Measure fallback and infeasibility by meal kind, dietary pattern and allergen set.
5. Smoke standalone Meal, requested DailyPlan, onboarding first plan and weekly Program.
6. Set `NUTRITION_CULINARY_RAW_FALLBACK_ENABLED=false` only after every gate passes.
