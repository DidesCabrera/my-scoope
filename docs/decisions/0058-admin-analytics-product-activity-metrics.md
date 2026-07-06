# 0058 · Admin Analytics product activity metrics

Status: accepted
Date: 2026-07-04

## Context

After ADM04, `admin_analytics` can observe the executive overview, commercial
accounts data and AI Assistant operations. The next strategic gap is product
activity inside `notas`, where the user actually builds nutritional value through
Foods, Meals, DailyPlans, Programs, Comparisons, Shares and proposals.

This data should remain owned by `notas`. `admin_analytics` should consume it as
read-only aggregated intelligence.

## Decision

Add an ADM05 staff-only page:

```text
/staff/analytics/product-activity/
```

The page is implemented in `admin_analytics` with:

```text
selectors/product_activity.py
services/product_activity.py
templates/admin_analytics/product_activity.html
```

The page reads existing `notas` operational tables and presents:

```text
Weekly Active Nutrition Builders
Foods / Meals / DailyPlans / Programs created in 7d and 30d
Draft/public/fork counts
MealFood, DailyPlanMeal and ProgramDay composition depth
DailyPlan source distribution
Program week depth
SavedComparison usage by kind
Share activity by type
Top nutrition builders
NutritionProposal created/applied signals
```

## Boundaries

ADM05 does not create analytical models, background jobs or snapshots.

It must not mutate `notas` entities. The page is staff-only and read-first.

Food quality is intentionally kept light in ADM05 because deep catalog quality
belongs to ADM06 / Food Catalog metrics.

## Consequences

Product operation can now answer whether users are creating real nutritional
assets, which entities are being used, whether Programs have real depth and
whether sharing/comparisons/proposals are contributing to activation.

Future patches can add filters, cohort views and stronger time-series support
without moving product behavior into `admin_analytics`.
