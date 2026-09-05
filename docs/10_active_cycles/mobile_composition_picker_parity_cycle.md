# Mobile Composition Picker Parity Cycle

Status: completed in repository — physical-device smoke remains external
Date: 2026-09-05
Cycle code: MCP00-MCP05

## Objective

Bring the native add/replace composition flows to the same two-step product
contract used by the responsive web experience:

1. select or create a reusable entity;
2. configure it and review the complete resulting entity before committing.

The mobile API remains authoritative for projections. React Native renders the
returned nutrition, structure and comparison panels and does not reproduce
nutrition calculations.

## Baseline findings

- The three native flows already separate selection and configuration through
  independent routes.
- Food-to-Meal and Meal-to-DailyPlan previews only return before/after aggregate
  nutrition; they omit the resulting Food/Meal panel rows.
- DailyPlan-to-Program validates replacements but returns no impact projection.
- Meal and DailyPlan replacement routes exist, while a MealFood can only be
  resized or deleted from the native edit panel even though the domain command
  already supports replacing its Food.
- Library entity cards, Food/Meal panels and the Program day-comparison panel
  already provide the native UI-system building blocks required by the result
  previews.

## Invariants

- Preview endpoints are read-only and owner-scoped.
- Commit endpoints continue to delegate to established domain commands.
- Replacement confirmation remains mandatory for occupied Program days.
- Preview rows are marked as projected and never expose a persisted relation id
  for a relation that does not exist yet.
- API additions are additive within `/api/v1`; existing selection, impact and
  confirmation fields remain available.
- The app consumes server-derived calories, macros, allocations and PPK.

## Execution order

### MCP00 — Contract and regression map

Status: completed.

- Trace native routes, state, source lists, preview/commit endpoints and return
  navigation.
- Trace ownership checks and the command used by every mutation.
- Identify reusable UI-system entity and comparison components.
- Record missing add/replace behavior and baseline contract tests.

### MCP01 — Projected-result API contract

Status: completed.

- Add a typed `result` object containing the resulting entity identity,
  nutrition, structural indicators and a standard library panel.
- Add optional MealFood replacement context to Food picker payloads.
- Keep the current preview fields for compatible clients.
- Cover response schemas and ownership boundaries with API tests.

### MCP02 — Meal result and Food replacement

Status: completed.

- Project the target Meal with the configured Food quantity.
- Remove the replaced MealFood from the projection and preserve its persisted
  relation on commit.
- Add a replace action to the native Food edit panel.
- Render the resulting Meal card with its Food tabs in step two.

### MCP03 — DailyPlan result

Status: completed.

- Project the target DailyPlan with the configured Meal, time and note.
- Render the resulting DailyPlan card with its Meal tabs in step two.
- Preserve existing add and replacement commit semantics.

### MCP04 — Program week result

Status: completed.

- Project all seven days of the selected week after assigning the DailyPlan to
  one or more selected days.
- Return server-derived day nutrition, PPK and week totals.
- Render the native plan-comparison tabs and replacement indicators in step two.

### MCP05 — Hardening and closure

Status: completed.

- Update TypeScript source-contract tests and focused Django API tests.
- Regenerate and check the committed mobile OpenAPI document.
- Run Django checks, focused backend tests, strict TypeScript, lint and mobile
  tests.
- Record evidence and residual external/manual validation in this cycle.

## Completion criteria

- All three native pickers visibly implement selection then configuration plus a
  complete projected result.
- Food, Meal and DailyPlan replacements use the same selector grammar as adds.
- The API response contains enough information to render every result without
  client-side nutrition math or a second target-detail fetch.
- Focused backend and mobile contracts cover add, replace and multi-day week
  projections.
- The OpenAPI artifact and this cycle document describe the delivered contract.

## Delivered result

- Each of the three native composition pickers retains its dedicated selection
  route and now renders a complete server-projected result in configuration.
- Meal results use the standard Food panels; DailyPlan results use the standard
  Meal panels; Program results use the standard seven-day comparison tabs.
- Projected Food, Meal and week-day rows visibly identify additions and
  replacements.
- Meal Food edit mode now opens the Food picker for replacement, preloads the
  existing quantity and commits through `update_meal_food` while preserving the
  relation id.
- The API carries configured quantity, time and note into the result structure,
  and carries day nutrition and PPK into the projected week.
- Existing impact and confirmation fields remain intact; the Week picker that
  only appends an empty week remains compatible through a nullable `result`.
- Post-integration refinements keep the configuration card fixed below the
  native header, remove redundant change-selection and configuration headings,
  and use the web-equivalent icons for portion, time, note and weekdays.
- Portion and weekday changes retain the current impact card while a debounced
  projection refresh runs. Commit is disabled until the successful projection
  key matches the current configuration payload.
- Contextual Food editing inside a DailyPlan returns both the resulting Meal and
  resulting DailyPlan, allowing the user to evaluate both levels before commit.
- The projected Program week intentionally renders its title and comparison
  table without a redundant KPI block.
- The stable product contract now lives in
  `docs/00_current/features/mobile_composition_pickers.md`.

## Validation evidence

- `scripts/ci_fast_checks.sh`: passed; repository hygiene, debt budgets,
  architecture, migrations, OpenAPI drift, document registry and 96 regression
  tests are green.
- CI recovery after integration replaced obsolete picker E2E selectors with
  assertions against the visible resulting Meal and DailyPlan cards. The full
  Chromium suite passes 29 scenarios, including add/edit quantity updates and
  DPM search.
- The mobile source-contract suite centralizes its repeated matching helpers;
  the enforced debt budget passes at 88 source reads and 454 source-regex
  assertions without increasing the configured ceiling of 530.
- Complete `mobile_api` suite: 64 tests passed, including libraries,
  composition projection, v1 contract and architecture.
- React Native: strict TypeScript passed, Expo lint passed, 60 source/contract
  tests passed and the 44-route Expo web export completed.
- The complete Django coverage gate passes 1,850 tests at 78% total coverage.
- Focused Python lint and schema type checking passed.
- No database migration was introduced.

## External follow-up

- Exercise add and replace once per picker on a physical iPhone, including a
  multi-day Program assignment, to validate touch ergonomics and scroll behavior
  with production-sized libraries. This is a release smoke, not unfinished
  repository implementation.
