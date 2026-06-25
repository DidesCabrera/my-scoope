# DOMAIN

This document explains the conceptual domain of the platform.

Entities:
- Food: atomic nutritional unit (macros per 100g)
- Meal: composition of foods via MealFood
- DailyPlan: composition of meals via DailyPlanMeal
- Program: composition of daily plans via ProgramDay

Intermediate tables (MealFood, DailyPlanMeal, ProgramDay) are FIRST-CLASS citizens.
They are not join tables; they hold meaning (quantity, time, note, snapshot).

No entity mutates lower-level data.
Higher levels aggregate, never redefine.