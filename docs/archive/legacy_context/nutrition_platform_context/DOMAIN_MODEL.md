# Domain Model

Hierarchy:

Food
 └── Meal (Food + quantity)
      └── DailyPlan (Meals + schedule)
           └── Program (DailyPlans + dates)

Rules:
- Each level aggregates data from the level below
- No duplicated nutritional data
- Higher levels expose emergent properties
