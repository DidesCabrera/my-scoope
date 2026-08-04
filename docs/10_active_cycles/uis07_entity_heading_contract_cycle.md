# UIS07 — Entity Heading Contract Cycle

Status: completed
Date: 2026-07-19
Cycle code: UIS07

## Objective

Give list cards, detail heroes and nested Program entities one shared heading, indicator and metadata anatomy.

## Delivered

- Declared `entity-heading`, `entity-heading__main`, `entity-heading__aside`, `entity-indicators` and `entity-metadata`.
- Applied the contract to shared Food/Meal/DailyPlan partials and to Program/Program Week compositions.
- Kept `card-title-comp`, `main-title`, `icons-title`, `structural-indicators` and `metadata` as migration aliases.

## Acceptance

Programs uses the same heading and indicator rules as the other entities while retaining its week-specific content.

