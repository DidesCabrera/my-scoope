# Nutrition Panel Energy Metrics Cycle

Status: completed
Date: 2026-08-11
Cycle code: NPE00-NPE05

## Objective

Make the energy contribution and intrinsic macronutrient composition of every
nutrition-table entity explicit without changing the meaning of the existing
contextual Alloc metrics.

## Metric contract

Each rendered relationship row exposes four complementary metric groups:

- `total_kcal`: absolute calories contributed by the row entity.
- `kcal_share`: percentage of the parent container's total calories contributed
  by the row entity.
- `kcal_distribution.protein|carbs|fat`: intrinsic percentage of the row
  entity's calories produced by each macronutrient. The three values are
  normalized against the row's own macro calories and sum to 100% when the row
  has energy; an energy-free row exposes three zeros.
- `alloc_protein|alloc_carbs|alloc_fat`: existing contextual contribution of
  each row macro to the equivalent parent macro total. Its semantics do not
  change.

The distribution uses the established energy factors (4 kcal/g protein,
4 kcal/g carbohydrate and 9 kcal/g fat). All four new percentages are derived
values; this cycle does not add database columns or migrations.

## Scope

- Food rows inside Meals.
- Meal rows inside DailyPlans.
- Aggregated Food rows in DailyPlan and Program contexts.
- Proposal entity rows that reuse the same nutrition panels.
- Shared responsive web components, templates, styles and focused tests.

The native Expo client is outside this cycle because it does not consume these
Django panel templates.

## Patches

### NPE00 — Contract and baseline

- Freeze the semantic distinction between contextual Alloc and intrinsic energy
  distribution.
- Inventory all direct builders and cached summary paths that feed the shared
  tables.

### NPE01 — Derived metric projection

- Add one pure domain calculation for intrinsic macro-calorie distribution.
- Project the distribution through live view-model builders, proposal builders
  and versioned DailyPlan/Program summary caches.

### NPE02 — Shared visual components

- Extend the existing allocation cell with a calorie variant for `kcal_share`.
- Add a shared stacked macro-calorie distribution bar using nutrition tokens.
- Hide a segment percentage automatically when the segment cannot contain it,
  while retaining an accessible full-text label on the component.

### NPE03 — Desktop tables

- Separate absolute kcal and `% kcal` into independent columns.
- Add one distribution column after the three macro-gram columns.
- Adjust Food, Meal and edit-grid widths without changing panel behavior.

### NPE04 — Mobile panel split

- Add a `Calorías` tab with entity, kcal and `% kcal` columns.
- Keep `Macros` focused on entity, P/C/F grams and the distribution bar.
- Leave `Alloc` unchanged.
- Preserve the existing quantity/menu and edit tabs.

### NPE05 — Confidence and closure

- Test normalization, zero-energy behavior and row projection.
- Test cache-versioned projections and locale-independent CSS values.
- Run Django checks, focused regressions and responsive visual QA.
- Promote the new component into the current UI inventory and mark this cycle
  completed once the evidence is green.

## Acceptance

- Absolute kcal and contextual `% kcal` never share the same visual cell.
- A row with energy has a P/C/F calorie distribution totaling 100% within normal
  floating-point tolerance.
- A zero-energy row renders a stable empty distribution without division errors.
- Stacked segments omit interior numbers while preserving their accessible
  P/C/F meaning.
- Desktop tables expose all metrics in one row.
- Responsive web panels expose `Calorías`, `Macros` and the unchanged `Alloc`
  views with no horizontal page overflow at the supported panel widths.
- Cached and uncached page paths produce the same metric contract.

## Risk and rollback

The main risks are stale cached summaries, invalid localized CSS custom-property
values and crowded responsive grids. Cache versions are bumped with the contract,
all CSS numeric values use `unlocalize`, and the old contextual Alloc fields remain
untouched. Rollback is limited to templates/styles plus the additive derived
fields; no persisted nutrition data changes.

## Delivered

- Added the pure `macro_kcal_distribution` domain calculation.
- Projected `kcal_distribution` through live builders, proposal cards and
  versioned DailyPlan/Program summary caches.
- Corrected proposal-row Alloc projection so it is contextual like operational
  relationship rows.
- Added the shared stacked distribution component with an accessible full label,
  no interior values, Alloc-equivalent height and a regular Alloc column width.
- Split kcal and `% kcal` on desktop Food/Meal tables and their edit variants.
- Added responsive `Calorías` panels and refocused `Macros` panels on grams plus
  intrinsic distribution, leaving `Alloc` unchanged.
- Extended the UI System inventory and kept `data_grid.css` within its enforced
  debt budget by isolating the new component styles.

## Validation evidence

```text
Django focused metric/cache/localization tests -> 9 passed
Proposal and proposal-view regressions          -> 48 passed
Read/performance contract regressions           -> 12 passed
Repository fast checks                          -> passed (95 tests)
Complete Django suite                           -> 1,756 passed in 272.451s

Responsive browser QA
  -> 1280x900 Food and Meal desktop grids fit all new columns
  -> 390x844 Calorías and Macros panels have no page overflow
  -> P/C/F percentages remain available through the accessible component label
  -> Alloc panel retains entity + P% + C% + F%
  -> browser console reported no warnings or errors
```

The browser smoke used a disposable migrated SQLite database and deterministic
E2E fixture graph. The temporary server and database were removed after QA; the
developer database was not modified.
