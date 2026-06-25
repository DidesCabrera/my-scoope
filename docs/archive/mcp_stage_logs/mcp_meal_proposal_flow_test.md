# MCP Meal Proposal Flow Test

## Purpose

This document records the MCP flow for creating a reviewable meal proposal in My Scoope.

This stage validates that MCP can:

```txt
list readable foods
use real food IDs
create a reviewable meal proposal
attach nutrition simulation
avoid creating final Meal records
avoid mutating final DailyPlans
```

The tested flow is:

```txt
MCP Inspector
  -> FastMCP protocol wrapper
  -> dispatch_tool_call
  -> MyscoopeAPIClient
  -> Django API Adapter
  -> Internal AI Tools
  -> Food catalog query
  -> Proposal payload validation
  -> Nutrition simulation query
  -> NutritionProposal
```

---

## Stage

This document records the completion of:

```txt
Etapa 2 — Crear propuesta de comida desde MCP
```

Stage distribution:

| Block | Task | Weight | Status |
|---:|---|---:|---|
| 1 | Create `list_food_catalog_for_planning` query | 20% | Completed |
| 2 | Expose MCP tool `list_food_catalog` | 15% | Completed |
| 3 | Create `create_validated_meal_proposal` tool | 30% | Completed |
| 4 | Attach nutrition simulation to proposal | 20% | Completed |
| 5 | E2E test and documentation | 15% | Completed |

Total:

```txt
100% completed
```

---

## Required Services

Django must be running locally:

```bash
python manage.py runserver
```

Expected Django base URL:

```txt
http://127.0.0.1:8000/app
```

MCP Inspector must be running:

```bash
npx @modelcontextprotocol/inspector
```

---

## MCP Inspector Configuration

Transport:

```txt
STDIO
```

Command:

```txt
/Users/felipedides/Desktop/proyecto_django/venv/bin/python
```

Arguments:

```txt
-m myscoope_mcp.run_protocol_server
```

Environment variables:

```txt
PYTHONPATH=mcp_server
MYSCOOPE_API_BASE_URL=http://127.0.0.1:8000/app
```

Do not use `--check` in MCP Inspector.

---

# Step 1: List Food Catalog

Tool:

```txt
list_food_catalog
```

Example arguments:

```json
{
  "search": "pollo",
  "limit": 25
}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "catalog": {
      "foods": [
        {
          "food_id": 1,
          "name": "Pechuga pollo",
          "protein": 31.0,
          "carbs": 0.0,
          "fat": 3.6,
          "kcal_per_100g": 156.4,
          "unit": "g",
          "source": "user"
        }
      ],
      "count": 1,
      "limit": 25,
      "search": "pollo"
    }
  },
  "error": null
}
```

This confirms that MCP can discover real food IDs available for nutrition planning.

---

# Step 2: Create Validated Meal Proposal

Tool:

```txt
create_validated_meal_proposal
```

Example arguments:

```json
{
  "dailyplan_id": 128,
  "title": "Propuesta MCP - Almuerzo IA",
  "summary": "Comida propuesta desde MCP usando alimentos reales y cantidades específicas.",
  "targets": {
    "protein": 60,
    "total_kcal": 500
  },
  "proposed_payload": {
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
}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "proposal": {
      "id": 1,
      "dailyplan_id": 128,
      "status": "pending_review",
      "title": "Propuesta MCP - Almuerzo IA",
      "proposed_payload": {
        "intent": "create_meal",
        "meal": {
          "name": "Almuerzo IA",
          "foods": []
        }
      },
      "validation_summary": {
        "payload_validation": {
          "is_valid": true,
          "intent": "create_meal"
        },
        "simulation": {
          "intent": "create_meal",
          "meal": {
            "name": "Almuerzo IA",
            "foods": [],
            "kpis": {}
          },
          "dailyplan": null
        }
      },
      "is_reviewable": true,
      "is_final": false
    }
  },
  "error": null
}
```

---

# Expected Proposal Contents

A successful meal proposal should include:

```txt
status: pending_review
proposed_payload.intent: create_meal
validation_summary.payload_validation.is_valid: true
validation_summary.simulation.intent: create_meal
validation_summary.simulation.meal.name
validation_summary.simulation.meal.foods
validation_summary.simulation.meal.kpis
is_reviewable: true
is_final: false
```

The simulation should include:

```txt
food names
quantities
protein
carbs
fat
kcal_protein
kcal_carbs
kcal_fat
total_kcal
allocation percentages
ppk when user weight is available
```

---

# Product Boundary

This flow creates a reviewable proposal.

It does not:

```txt
create final Meal records
create final MealFood records
create final DailyPlan records
modify existing DailyPlans
approve proposals
apply proposals
```

This boundary is intentional.

MCP can propose a meal, but final application remains inside My Scoope's authenticated human review flow.

---

# Food Visibility Boundary

The food catalog and simulation use the existing readable food boundary.

Allowed foods:

```txt
system foods
foods created by the authenticated user
```

Rejected foods:

```txt
private foods created by another user
```

This prevents MCP from proposing meals with inaccessible food IDs.

---

# Validated Capabilities

This stage validates:

```txt
list_food_catalog: ok
create_validated_meal_proposal: ok
proposal payload validation: ok
meal nutrition simulation: ok
proposal persistence: ok
MCP routing: ok
API Adapter endpoint: ok
internal AI tool wrapper: ok
```

---

# Troubleshooting

## MCP Inspector does not make nested objects easy to edit

Some MCP Inspector versions may make nested object parameters harder to fill manually.

The most important nested object is:

```txt
proposed_payload
```

Expected shape:

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

If the Inspector UI is uncomfortable, validate the same payload through the Django API Adapter test or use a simpler payload first.

---

## Missing food IDs

Before creating a meal proposal, call:

```txt
list_food_catalog
```

Use the returned `food_id` values.

Do not invent food IDs.

---

## Unreadable food IDs

If the proposal references a private food from another user, simulation should fail.

This is expected.

---

# Relevant Modules

```txt
notas/application/queries/food_catalog_queries.py
notas/application/dto/proposal_payloads.py
notas/application/validation/proposal_payload_validators.py
notas/application/queries/proposal_simulation_queries.py
notas/application/services/commands/proposal_commands.py
notas/application/ai_tools/read_tools.py
notas/application/ai_tools/proposal_tools.py
notas/interface/api/ai_tools.py
mcp_server/myscoope_mcp/tools.py
mcp_server/myscoope_mcp/tool_handlers.py
mcp_server/myscoope_mcp/dispatcher.py
mcp_server/myscoope_mcp/protocol_server.py
```

---

# Relevant Tests

```txt
notas/tests/test_food_catalog_queries.py
notas/tests/test_ai_food_catalog_tools.py
notas/tests/test_ai_tools_api_food_catalog_endpoint.py
notas/tests/test_create_validated_meal_proposal_command.py
notas/tests/test_ai_meal_proposal_tools.py
notas/tests/test_ai_tools_api_meal_proposal_endpoint.py
notas/tests/test_proposal_payload_dto.py
notas/tests/test_proposal_payload_validators.py
notas/tests/test_proposal_simulation_queries.py
mcp_server/tests/test_mcp_food_catalog_tool.py
mcp_server/tests/test_mcp_meal_proposal_tool.py
```

Recommended command:

```bash
python manage.py test notas.tests.test_food_catalog_queries notas.tests.test_ai_food_catalog_tools notas.tests.test_ai_tools_api_food_catalog_endpoint notas.tests.test_create_validated_meal_proposal_command notas.tests.test_ai_meal_proposal_tools notas.tests.test_ai_tools_api_meal_proposal_endpoint notas.tests.test_proposal_payload_dto notas.tests.test_proposal_payload_validators notas.tests.test_proposal_simulation_queries mcp_server/tests
```

---

# Final Outcome

At the end of this stage, MCP can create real, reviewable meal proposals using existing foods and quantities.

The proposal includes a nutrition simulation, but it does not create final nutrition objects.

This is the correct boundary before implementing human review/apply flows.

---

# Recommended Next Stage

The next natural stage is:

```txt
Etapa 3 — Crear propuesta de DailyPlan desde MCP
```

Suggested distribution:

| Block | Task | Weight |
|---:|---|---:|
| 1 | Extend proposal command for `create_dailyplan` payloads | 20% |
| 2 | Create `create_validated_dailyplan_build_proposal` tool | 25% |
| 3 | Attach dailyplan-level nutrition simulation | 25% |
| 4 | Expose MCP tool and API Adapter endpoint | 20% |
| 5 | E2E test and documentation | 10% |

Expected result:

```txt
MCP can propose a complete DailyPlan made of proposed meals, foods and quantities.
```