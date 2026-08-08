# UIS05 — Entity Card Contract Cycle

Status: completed
Date: 2026-07-19
Cycle code: UIS05

## Objective

Give Food, Meal, DailyPlan and Program cards one explicit structural contract without forcing their domain content into a single parameter-heavy template.

## Delivered

- Added `entity_card.css` as owner of the card shell, main row, KPI region and footer.
- Added semantic classes to Food, Meal, DailyPlan and Program cards.
- Added the `entity-card--nested` contract to Program Week cards.
- Preserved legacy `.card*` selectors as aliases.
- Removed shared card declarations from `card_child.css`, leaving it responsible for contextual variants.

## Non-goals

- Merge every entity template into one include.
- Standardize domain-specific KPI content.
- Redesign Proposal/Inbox message cards.
- Remove compatibility aliases.

## Acceptance

- Entity cards retain existing appearance and behavior.
- Programs consumes the same card surface contract as the other entity libraries.
- Feature CSS no longer owns the Program Week base surface.

## Validation evidence

```text
python manage.py check
  -> no issues

python manage.py test notas.tests --keepdb
  -> 1,145 tests passed

Local visual smoke
  -> Meal, DailyPlan and Program library cards: desktop
  -> nested Meal card in DailyPlan: desktop + 390px mobile
  -> Program Week card: desktop + 390px mobile
  -> computed surface, padding, border and radius verified
  -> no browser console warnings or errors
```
