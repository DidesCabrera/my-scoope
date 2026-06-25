# Rich Proposal Payload Contracts

## Purpose

This document defines the first formal contract for rich nutrition proposal payloads in My Scoope.

The goal of this stage is to allow AI/MCP flows to propose real nutrition structures, such as meals and daily plans, without directly mutating final user data.

This stage is intentionally read-only and proposal-oriented.

---

## Current Stage

This document records the completion of:

```txt
Etapa 1 — Contrato de propuestas ricas
```

The completed tasks are:

| Task | Description | Status |
|---:|---|---|
| 1 | Define `proposed_payload` schema for `create_meal` | Completed |
| 2 | Define `proposed_payload` schema for `create_dailyplan` | Completed |
| 3 | Add explicit payload validators | Completed |
| 4 | Add read-only nutrition simulation queries | Completed |
| 5 | Document final result and tests | Completed |

Total:

```txt
100% completed
```

---

## Why This Layer Exists

The previous MCP validation stage proved that MCP can create reviewable `NutritionProposal` records.

This stage extends the meaning of `proposed_payload`.

Before this stage, a proposal could contain a minimal structure such as:

```json
{
  "intent": "adjust_dailyplan_to_targets",
  "suggested_changes": []
}
```

After this stage, the system can formally understand richer payloads such as:

```txt
create_meal
create_dailyplan
```

These payloads are still proposals. They do not create final Meals or DailyPlans.

---

## Product Boundary

The rich proposal payload layer does not:

```txt
create Meal records
create DailyPlan records
create MealFood records
modify existing DailyPlans
approve proposals
apply proposals
```

It does:

```txt
parse proposed payloads
validate proposed payloads
normalize proposed payloads
simulate nutrition read-only
return serializable projections
```

This keeps the AI/MCP boundary safe.

---

# Supported Intents

## 1. create_meal

A `create_meal` payload represents a proposed meal with foods and quantities.

Example:

```json
{
  "intent": "create_meal",
  "meal": {
    "name": "Almuerzo alto en proteína",
    "foods": [
      {
        "food_id": 10,
        "quantity": 180,
        "unit": "g"
      },
      {
        "food_id": 20,
        "quantity": 120.5
      }
    ]
  }
}
```

Normalized result:

```json
{
  "intent": "create_meal",
  "meal": {
    "name": "Almuerzo alto en proteína",
    "foods": [
      {
        "food_id": 10,
        "quantity": 180.0,
        "unit": "g"
      },
      {
        "food_id": 20,
        "quantity": 120.5,
        "unit": "g"
      }
    ]
  }
}
```

Rules:

```txt
intent must be create_meal
meal must be an object
meal.name must be a non-empty string
meal.foods must be a non-empty list
each food item must be an object
food_id must be an integer
quantity must be numeric and positive
unit must be a non-empty string
unit defaults to g
```

---

## 2. create_dailyplan

A `create_dailyplan` payload represents a proposed daily plan with one or more meals.

Example:

```json
{
  "intent": "create_dailyplan",
  "dailyplan": {
    "name": "Día entrenamiento IA",
    "meals": [
      {
        "hour": "9:05",
        "note": "Desayuno",
        "meal": {
          "name": "Desayuno alto en energía",
          "foods": [
            {
              "food_id": 1,
              "quantity": 80
            }
          ]
        }
      }
    ]
  }
}
```

Normalized result:

```json
{
  "intent": "create_dailyplan",
  "dailyplan": {
    "name": "Día entrenamiento IA",
    "meals": [
      {
        "hour": "09:05",
        "note": "Desayuno",
        "meal": {
          "name": "Desayuno alto en energía",
          "foods": [
            {
              "food_id": 1,
              "quantity": 80.0,
              "unit": "g"
            }
          ]
        }
      }
    ]
  }
}
```

Rules:

```txt
intent must be create_dailyplan
dailyplan must be an object
dailyplan.name must be a non-empty string
dailyplan.meals must be a non-empty list
dailyplan.meals must not exceed 10 items
each dailyplan meal must be an object
hour may be null or empty
hour is normalized to HH:MM
hour must be in valid 00:00-23:59 range
note defaults to an empty string
nested meal must follow meal rules
nested foods must follow food item rules
```

---

# DTO Layer

The DTO contracts live in:

```txt
notas/application/dto/proposal_payloads.py
```

Main DTOs:

```txt
ProposedFoodItemDTO
ProposedMealDTO
ProposedDailyPlanMealDTO
ProposedDailyPlanDTO
ProposedMealPayloadDTO
ProposedDailyPlanPayloadDTO
```

Main parsing functions:

```txt
parse_proposed_food_item_payload
parse_proposed_meal_payload
parse_proposed_dailyplan_payload
parse_proposal_payload
```

The parser layer is strict.

Invalid payloads raise `ValueError` with stable error codes.

Examples:

```txt
unsupported_proposal_payload_intent
proposed_meal_name_required
proposed_food_item_quantity_must_be_positive
proposed_dailyplan_meal_hour_out_of_range
```

---

# Validation Layer

The validation layer lives in:

```txt
notas/application/validation/proposal_payload_validators.py
```

Main functions:

```txt
validate_proposal_payload
validate_proposal_payload_or_raise
is_create_meal_payload
is_create_dailyplan_payload
```

`validate_proposal_payload` returns a structured result:

```json
{
  "is_valid": false,
  "intent": "create_meal",
  "errors": [
    {
      "code": "proposed_meal_name_required",
      "message": "Meal proposal requires a non-empty meal name.",
      "field": "meal.name"
    }
  ],
  "parsed_payload": null
}
```

This is useful for:

```txt
MCP tool responses
API Adapter responses
UI review screens
debugging invalid AI outputs
```

---

# Simulation Layer

The simulation layer lives in:

```txt
notas/application/queries/proposal_simulation_queries.py
```

Main function:

```txt
simulate_proposal_payload
```

This function:

```txt
validates the payload
loads readable foods for the user
calculates macros
calculates calories
calculates allocation percentages
calculates ppk when user weight is available
returns a serializable projection
```

It supports:

```txt
create_meal
create_dailyplan
```

It is read-only.

---

## create_meal Simulation Example

Input:

```json
{
  "intent": "create_meal",
  "meal": {
    "name": "Almuerzo IA",
    "foods": [
      {
        "food_id": 1,
        "quantity": 200,
        "unit": "g"
      }
    ]
  }
}
```

Output shape:

```json
{
  "intent": "create_meal",
  "meal": {
    "name": "Almuerzo IA",
    "foods": [
      {
        "food_id": 1,
        "food_name": "Pechuga pollo",
        "quantity": 200.0,
        "unit": "g",
        "protein": 62.0,
        "carbs": 0.0,
        "fat": 7.2,
        "kcal_protein": 248.0,
        "kcal_carbs": 0.0,
        "kcal_fat": 64.8,
        "total_kcal": 312.8
      }
    ],
    "kpis": {
      "total_kcal": 312.8,
      "protein": 62.0,
      "carbs": 0.0,
      "fat": 7.2,
      "kcal_protein": 248.0,
      "kcal_carbs": 0.0,
      "kcal_fat": 64.8,
      "alloc_protein": 79.28,
      "alloc_carbs": 0.0,
      "alloc_fat": 20.72,
      "ppk": 0.62
    }
  },
  "dailyplan": null
}
```

---

## create_dailyplan Simulation Example

Input:

```json
{
  "intent": "create_dailyplan",
  "dailyplan": {
    "name": "Día entrenamiento IA",
    "meals": [
      {
        "hour": "09:00",
        "note": "Desayuno",
        "meal": {
          "name": "Desayuno IA",
          "foods": [
            {
              "food_id": 1,
              "quantity": 100
            }
          ]
        }
      }
    ]
  }
}
```

Output shape:

```json
{
  "intent": "create_dailyplan",
  "meal": null,
  "dailyplan": {
    "name": "Día entrenamiento IA",
    "meals": [
      {
        "hour": "09:00",
        "note": "Desayuno",
        "meal": {
          "name": "Desayuno IA",
          "foods": [],
          "kpis": {}
        }
      }
    ],
    "kpis": {
      "total_kcal": 0.0,
      "protein": 0.0,
      "carbs": 0.0,
      "fat": 0.0,
      "ppk": null
    }
  }
}
```

---

# Food Visibility Boundary

The simulation query only uses foods readable by the current user.

It allows:

```txt
system foods
foods created by the user
```

It rejects:

```txt
private foods created by another user
```

This keeps proposed payload simulation aligned with the existing application read boundary.

---

# Tests

Relevant test files:

```txt
notas/tests/test_proposal_payload_dto.py
notas/tests/test_proposal_payload_validators.py
notas/tests/test_proposal_simulation_queries.py
```

Recommended command:

```bash
python manage.py test notas.tests.test_proposal_payload_dto notas.tests.test_proposal_payload_validators notas.tests.test_proposal_simulation_queries
```

Recommended broader regression command:

```bash
python manage.py test notas.tests.test_ai_proposal_tools notas.tests.test_proposal_commands mcp_server/tests
```

---

# Stage Outcome

This stage establishes the internal contract required before exposing richer MCP tools.

The system can now safely understand and simulate:

```txt
AI-proposed meals
AI-proposed dailyplans
foods with quantities
meal-level nutrition projections
dailyplan-level nutrition projections
```

The next stage should expose this safely through MCP/API tools.

---

# Recommended Next Stage

The next natural stage is:

```txt
Etapa 2 — Crear propuesta de comida desde MCP
```

Suggested tasks:

| Task | Description | Weight |
|---:|---|---:|
| 1 | Create food catalog query for planning | 20% |
| 2 | Expose `list_food_catalog` MCP tool | 15% |
| 3 | Create `create_validated_meal_proposal` tool | 30% |
| 4 | Attach simulation result to proposal payload/summary | 20% |
| 5 | E2E test and documentation | 15% |

Expected result:

```txt
MCP can create real, reviewable meal proposals with foods and quantities.
```