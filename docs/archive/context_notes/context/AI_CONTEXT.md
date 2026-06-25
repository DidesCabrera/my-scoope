# AI CONTEXT – Meal Platform


This project is a nutrition platform built in Django.

Core hierarchy:
Food → Meal → DailyPlan → Program

Key principles:
- All nutrition calculations live in models
- Macros are stored in grams, calories are derived
- Allocation (%) is calculated only after aggregation
- Forks preserve genealogy, copies are independent
- Draft → finalize flow is mandatory
- UI exposes all options but enforces permissions via helpers

Current state:
- Foods can be imported via Excel
- Meals calculate macros correctly
- DailyPlans and Programs aggregate nutrition
- Permissions handled via helper functions (can_publish, can_copy, can_fork)

DO NOT:
- Move nutrition logic to views
- Store calories in DB
- Break fork lineage

Author mindset:
The creator thinks in systems, not features.
