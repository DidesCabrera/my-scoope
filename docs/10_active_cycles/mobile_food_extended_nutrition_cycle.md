# Mobile Food Extended Nutrition Cycle

Status: completed
Date: 2026-10-11

## Objective

Expose the extended nutrition already preserved in the operational food snapshot on native food-detail screens, using the shared icon-free key/value table pattern.

## Scope

- Add saturated fat, total sugars, fiber and sodium to the mobile library food-detail contract.
- Render the four values per 100 g or 100 ml below the existing calorie and macro summary.
- Preserve the semantic difference between a measured zero and unavailable information.
- Reuse `Card`, `CardHeader` and `KeyValueTable` instead of introducing a feature-specific table.

## Safety boundaries

- Read from `notas.Food`, the operational snapshot used by Meals and planning; do not read live `CatalogFood` data from the mobile API.
- Keep the extended fields nullable and render null as `Sin información`.
- Do not infer, calculate or replace missing nutrients with zero.
- Do not change historical proposal or shared-resource snapshots, which do not currently preserve these four fields.
- Do not change Food Catalog publication or Knowledge Center content.

## Acceptance

- A stored zero renders as `0 g` or `0 mg`.
- A null renders as `Sin información`.
- The table has no icons and follows the shared attribute-table layout.
- The title reflects whether the food basis is 100 g or 100 ml.
- Existing food, meal, daily-plan and program detail contracts remain valid.

## Validation plan

1. Focused API test for nullable and zero-valued nutrients.
2. Focused mobile component test for formatting and shared table adoption.
3. Changed-file lint plus the focused mobile test through `ci_mobile_visual_check.sh`.
4. Regenerate and verify the committed mobile OpenAPI contract.

## Validation evidence

- `scripts/ci_fast_checks.sh`: passed, including debt budgets, Django checks, OpenAPI freshness, document registry and 102 structural tests.
- `mobile_api.tests.test_food_detail_navigation_api`: 3 tests passed.
- `scripts/ci_mobile_iteration.sh`: lint, TypeScript typecheck and 224 mobile tests passed.
- The staging simulator confirmed backward compatibility with the pre-change API: the new card remains hidden until the server returns `food_nutrition`.
