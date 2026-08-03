# Decision 0164: repeated test setup uses small composable builders

Date: 2026-08-02
Status: accepted
Cycle: TDG06

## Context

Account creation and basic nutrition graphs were repeated across many suites. The
duplication obscured the behavior under test and made harmless model-default changes
expensive. A large factory framework would add a new abstraction and dependency for
needs that are currently simple.

## Decision

- Provide explicit persistence builders for regular/staff users.
- Provide nutrition builders for Food, Meal, MealFood and DailyPlan with useful
  defaults and keyword overrides.
- Keep builders as ordinary functions that return real Django models.
- Migrate Admin Operations and selected query/proposal suites first; adopt them in
  other suites when those files are already changing.
- Preserve the fast structural gate as a separate feedback surface from the full
  regression suite.

## Consequences

- The six migrated suites remove 135 net lines of repetitive setup while keeping
  their scenario-specific values visible.
- There is no hidden fixture lifecycle, implicit database state or additional test
  dependency.
- Builders remain optional; unusual scenarios can still create models directly.
