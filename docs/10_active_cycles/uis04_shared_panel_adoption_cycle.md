# UIS04 — Shared Panel Adoption Cycle

Status: completed
Date: 2026-07-19
Cycle code: UIS04
Scope: Meals, DailyPlans, DPM and Programs

## Objective

Execute the first vertical UI System migration by making equivalent panel surfaces and tabs consume neutral shared classes without changing their product behavior.

## Delivered

- Added `content_panel.css` as the owner of the shared panel surface.
- Preserved `card-detail-block` and `main` as compatibility aliases.
- Migrated Meal, DailyPlan and DPM nested/main panels to the neutral contract.
- Migrated Program week, day, aggregation and chart panels to the same contract.
- Migrated Food/Meal/DailyPlan panel tabs, Program week tabs and generated chart tabs to `panel-tabs` / `panel-tab`.
- Removed duplicate Program surface and week-tab declarations now owned by shared components.

## Non-goals

- Redesign cards or details.
- Split all of `programs.css`.
- Remove legacy class names in the same patch.
- Migrate special surfaces such as Proposal, Inbox, Profile or Admin.

## Acceptance

- Django templates compile and application checks pass.
- Existing automated tests pass.
- Representative Meal, DailyPlan and Program pages retain their visual hierarchy.
- Program panel/tab appearance is governed by the same tokens and component CSS as the rest of the entity system.

## Validation evidence

```text
python manage.py check
  -> no issues

python manage.py test notas.tests --keepdb
  -> 1,145 tests passed

Local visual smoke
  -> Meal detail: desktop
  -> DailyPlan detail: desktop + 390px mobile
  -> Program list/detail: desktop + 390px mobile
  -> no browser console warnings or errors
```

The local smoke used an isolated copy of the development SQLite database. The copy was removed after validation and the source database was not modified.
