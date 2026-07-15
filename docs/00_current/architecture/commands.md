# Application Commands

Application commands centralize write operations in My Scoope.

They are located mainly in:

- `notas/application/services/commands/meal_commands.py`
- `notas/application/services/commands/dailyplan_commands.py`
- `notas/application/services/commands/food_commands.py`
- `notas/application/services/commands/share_commands.py`

## Why commands exist

Commands make the system usable from multiple interfaces:

- Django web views
- future REST API
- future MCP tools
- future internal AI assistant
- future mobile app backend

A view should call a command instead of performing database writes directly.

## Meal Commands

Main responsibilities:

- Create draft meals.
- Rename meals.
- Delete meals.
- Configure meals.
- Save foods inside meals.
- Create, update, delete, and reorder MealFood entries.
- Save/fork/copy meals for library or DailyPlan usage.
- Finish pending meals created from a DailyPlan context.

Key rule:

A Meal used inside a DailyPlan should be isolated from the original library Meal when appropriate.

## DailyPlan Commands

Main responsibilities:

- Create draft DailyPlans.
- Rename DailyPlans.
- Delete DailyPlans.
- Configure DailyPlans.
- Save/fork/copy DailyPlans.
- Add existing Meals to DailyPlans as isolated snapshots.
- Remove DailyPlanMeal entries.
- Update DailyPlanMeal metadata.
- Reorder DailyPlanMeal entries.
- Replace DailyPlanMeal snapshots.
- Create empty Meals inside a DailyPlanMeal.
- Create pending Meals from a DailyPlan context.

Key rule:

When a Meal from the library is added to a DailyPlan, the system should work with a fork/snapshot so future edits do not affect the original library Meal.

## Food Commands

Main responsibilities:

- Create user foods.
- Update user foods.
- Bulk-create foods from imported rows.

Food commands are part of the nutrition core because Food is the base entity for Meal and DailyPlan nutrition calculations.

## Share Commands

Main responsibilities:

- Create DailyPlan shares.
- Accept, dismiss, and remove DailyPlan shares.
- Create Meal shares.
- Accept, dismiss, and remove Meal shares.

Sharing rules should stay outside views so future interfaces do not duplicate permission and state logic.

## Command Design Rules

Commands should:

- Receive explicit arguments.
- Return explicit result dataclasses.
- Use transactions where needed.
- Avoid request-specific behavior.
- Avoid rendering or redirects.
- Avoid direct UI assumptions.
- Raise controlled errors or simple exceptions for invalid operations.

Commands should not:

- Read `request.POST`.
- Call `messages`.
- Return `HttpResponse`.
- Render templates.
- Depend on JavaScript or HTML structure.

## Current Out-of-Scope Areas

The following areas still contain direct writes but are not part of the current nutrition-core command extraction:

- `notas/interface/views/admin_tools.py`
- `notas/interface/views/programs.py`

They should be handled in a future dedicated phase if they remain active product areas.