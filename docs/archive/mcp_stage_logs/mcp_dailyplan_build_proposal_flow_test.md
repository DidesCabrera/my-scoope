# MCP DailyPlan Build Proposal Flow Test

## Purpose

This document records the MCP flow for creating a reviewable DailyPlan build proposal in My Scoope.

This stage validates that MCP can propose a complete DailyPlan made of proposed meals, real foods and quantities, while keeping final nutrition data unchanged.

The tested flow is:

```txt
MCP Inspector
  -> FastMCP protocol wrapper
  -> dispatch_tool_call
  -> MyscoopeAPIClient
  -> Django API Adapter
  -> Internal AI Tools
  -> Proposal payload validation
  -> Nutrition simulation query
  -> NutritionProposal
```

---

## Stage

This document records the completion of:

```txt
Etapa 3 — Crear propuesta de DailyPlan desde MCP
```

Stage distribution:

| Block | Task | Weight | Status |
|---:|---|---:|---|
| 1 | Create `create_validated_dailyplan_build_proposal` command | 20% | Completed |
| 2 | Create AI tool and API Adapter endpoint | 20% | Completed |
| 3 | Expose MCP tool | 20% | Completed |
| 4 | Validate E2E with MCP Inspector | 25% | Completed |
| 5 | Final documentation | 15% | Completed |

Total:

```txt
100% completed
```

---

## Required Services

Django must be running locally with internal MCP auth enabled:

```bash
export MYSCOOPE_INTERNAL_API_TOKEN="dev-mcp-token"
export MYSCOOPE_INTERNAL_API_USERNAME="felipe"
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
MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token
```

Do not use `--check` in MCP Inspector.

---

# Step 1: List Food Catalog

Tool:

```txt
list_food_catalog
```

Arguments used:

```json
{
  "limit": 50
}
```

Successful result:

```json
{
  "ok": true,
  "data": {
    "catalog": {
      "foods": [
        {
          "food_id": 128,
          "name": "a nuevo egg TEST",
          "protein": 1,
          "carbs": 1,
          "fat": 1,
          "kcal_per_100g": 17,
          "unit": "g",
          "source": "user"
        },
        {
          "food_id": 129,
          "name": "food mod",
          "protein": 4,
          "carbs": 4,
          "fat": 1,
          "kcal_per_100g": 41,
          "unit": "g",
          "source": "system"
        },
        {
          "food_id": 130,
          "name": "sdfbsdfb",
          "protein": 4,
          "carbs": 4,
          "fat": 4,
          "kcal_per_100g": 68,
          "unit": "g",
          "source": "user"
        }
      ],
      "count": 3,
      "limit": 50,
      "search": null
    }
  },
  "error": null
}
```

This confirms that MCP can retrieve real food IDs available for planning.

---

# Step 2: Create DailyPlan Build Proposal

Tool:

```txt
create_validated_dailyplan_build_proposal
```

Arguments used:

```json
{
  "dailyplan_id": 128,
  "title": "Plan AI",
  "summary": "DailyPlan completo propuesto desde MCP usando alimentos reales.",
  "targets": {
    "protein": 190,
    "total_kcal": 2800
  },
  "proposed_payload": {
    "intent": "create_dailyplan",
    "dailyplan": {
      "name": "Día entrenamiento IA - prueba MCP",
      "meals": [
        {
          "hour": "09:00",
          "note": "Desayuno",
          "meal": {
            "name": "Desayuno IA",
            "foods": [
              {
                "food_id": 128,
                "quantity": 200,
                "unit": "g"
              }
            ]
          }
        }
      ]
    }
  }
}
```

Successful result:

```json
{
  "ok": true,
  "data": {
    "proposal": {
      "id": 2,
      "dailyplan_id": 128,
      "dailyplan_name": "Menú Dia Entrenamiento",
      "created_by_id": 8,
      "created_by_username": "felipe",
      "reviewed_by_id": null,
      "reviewed_by_username": null,
      "status": "pending_review",
      "source": "ai",
      "title": "Plan AI",
      "summary": "DailyPlan completo propuesto desde MCP usando alimentos reales.",
      "targets": {
        "protein": 190,
        "total_kcal": 2800
      },
      "current_snapshot": {
        "dailyplan_id": 128,
        "context": "dailyplan_build_proposal"
      },
      "proposed_payload": {
        "intent": "create_dailyplan",
        "dailyplan": {
          "name": "Día entrenamiento IA - prueba MCP",
          "meals": [
            {
              "hour": "09:00",
              "note": "Desayuno",
              "meal": {
                "name": "Desayuno IA",
                "foods": [
                  {
                    "food_id": 128,
                    "quantity": 200,
                    "unit": "g"
                  }
                ]
              }
            }
          ]
        }
      },
      "validation_summary": {
        "payload_validation": {
          "is_valid": true,
          "intent": "create_dailyplan"
        },
        "simulation": {
          "intent": "create_dailyplan",
          "meal": null,
          "dailyplan": {
            "name": "Día entrenamiento IA - prueba MCP",
            "meals": [
              {
                "hour": "09:00",
                "note": "Desayuno",
                "meal": {
                  "name": "Desayuno IA",
                  "foods": [
                    {
                      "food_id": 128,
                      "food_name": "a nuevo egg TEST",
                      "quantity": 200,
                      "unit": "g",
                      "protein": 2,
                      "carbs": 2,
                      "fat": 2,
                      "kcal_protein": 8,
                      "kcal_carbs": 8,
                      "kcal_fat": 18,
                      "total_kcal": 34
                    }
                  ],
                  "kpis": {
                    "total_kcal": 34,
                    "protein": 2,
                    "carbs": 2,
                    "fat": 2,
                    "kcal_protein": 8,
                    "kcal_carbs": 8,
                    "kcal_fat": 18,
                    "alloc_protein": 23.52941176470588,
                    "alloc_carbs": 23.52941176470588,
                    "alloc_fat": 52.94117647058824,
                    "ppk": 0.023809523809523808
                  }
                }
              }
            ],
            "kpis": {
              "total_kcal": 34,
              "protein": 2,
              "carbs": 2,
              "fat": 2,
              "kcal_protein": 8,
              "kcal_carbs": 8,
              "kcal_fat": 18,
              "alloc_protein": 23.52941176470588,
              "alloc_carbs": 23.52941176470588,
              "alloc_fat": 52.94117647058824,
              "ppk": 0.023809523809523808
            }
          }
        }
      },
      "is_reviewable": true,
      "is_final": false,
      "created_at": "2026-05-11T17:56:02.573375+00:00",
      "reviewed_at": null
    }
  },
  "error": null
}
```

---

# Step 3: Read Created Proposal

Tool:

```txt
read_proposal
```

Arguments:

```json
{
  "proposal_id": 2
}
```

Expected result:

```txt
ok: true
proposal.id: 2
proposal.status: pending_review
proposal.proposed_payload.intent: create_dailyplan
proposal.validation_summary.simulation.dailyplan exists
```

This verification completed successfully.

---

# Step 4: List User Proposals

Tool:

```txt
list_user_proposals
```

Arguments:

```json
{}
```

Expected result:

```txt
ok: true
proposal id 2 appears in the authenticated user's proposal list
proposal status is pending_review
```

This verification completed successfully.

---

# Validated Capabilities

This stage validates:

```txt
list_food_catalog: ok
create_validated_dailyplan_build_proposal: ok
read_proposal: ok
list_user_proposals: ok
proposal payload validation: ok
dailyplan nutrition simulation: ok
proposal persistence: ok
MCP routing: ok
API Adapter endpoint: ok
internal AI tool wrapper: ok
```

---

# Product Boundary

This flow creates a reviewable proposal.

It does not:

```txt
create final DailyPlan records
create final Meal records
create final MealFood records
modify existing DailyPlans
approve proposals
apply proposals
```

This boundary is intentional.

MCP can propose a complete DailyPlan, but final application remains inside My Scoope's authenticated human review flow.

---

# Simulation Validation

The simulation correctly calculated the proposed DailyPlan using food `128`.

Food used:

```txt
food_id: 128
name: a nuevo egg TEST
quantity: 200 g
protein per 100g: 1
carbs per 100g: 1
fat per 100g: 1
```

Expected simulated values:

```txt
protein: 2 g
carbs: 2 g
fat: 2 g
kcal_protein: 8
kcal_carbs: 8
kcal_fat: 18
total_kcal: 34
```

Observed values matched the expected simulation.

---

# Authentication Note

During E2E validation, MCP initially received a contract error because the API Adapter redirected unauthenticated requests to login.

The issue was resolved by configuring internal API authentication.

Django runtime:

```bash
export MYSCOOPE_INTERNAL_API_TOKEN="dev-mcp-token"
export MYSCOOPE_INTERNAL_API_USERNAME="felipe"
python manage.py runserver
```

MCP Inspector environment:

```txt
MYSCOOPE_API_AUTH_TOKEN=dev-mcp-token
```

The token sent by MCP must match the token expected by Django.

---

# MCP Inspector Nested Payload Note

When calling `create_validated_dailyplan_build_proposal`, the `proposed_payload` field must contain only the rich proposal payload:

```json
{
  "intent": "create_dailyplan",
  "dailyplan": {
    "name": "Día entrenamiento IA - prueba MCP",
    "meals": []
  }
}
```

Do not paste the full tool call object inside `proposed_payload`.

If the backend receives the wrong nested object, it may return:

```txt
unsupported_proposal_payload_intent
```

---

# Relevant Modules

```txt
notas/application/services/commands/proposal_commands.py
notas/application/ai_tools/proposal_tools.py
notas/interface/api/ai_tools.py
notas/application/dto/proposal_payloads.py
notas/application/validation/proposal_payload_validators.py
notas/application/queries/proposal_simulation_queries.py
notas/application/queries/food_catalog_queries.py
mcp_server/myscoope_mcp/tools.py
mcp_server/myscoope_mcp/tool_handlers.py
mcp_server/myscoope_mcp/dispatcher.py
mcp_server/myscoope_mcp/protocol_server.py
```

---

# Relevant Tests

```txt
notas/tests/test_create_validated_dailyplan_build_proposal_command.py
notas/tests/test_ai_dailyplan_build_proposal_tools.py
notas/tests/test_ai_tools_api_dailyplan_build_proposal_endpoint.py
notas/tests/test_proposal_payload_dto.py
notas/tests/test_proposal_payload_validators.py
notas/tests/test_proposal_simulation_queries.py
mcp_server/tests/test_mcp_dailyplan_build_proposal_tool.py
```

Recommended command:

```bash
python manage.py test notas.tests.test_create_validated_dailyplan_build_proposal_command notas.tests.test_ai_dailyplan_build_proposal_tools notas.tests.test_ai_tools_api_dailyplan_build_proposal_endpoint notas.tests.test_proposal_payload_dto notas.tests.test_proposal_payload_validators notas.tests.test_proposal_simulation_queries mcp_server/tests
```

---

# Final Outcome

At the end of this stage, MCP can create real, reviewable DailyPlan build proposals using existing foods and quantities.

The proposal includes a full DailyPlan-level nutrition simulation, but it does not create final nutrition objects.

This is the correct boundary before implementing human review/apply flows.

---

# Recommended Next Stage

The next natural stage is:

```txt
Etapa 4 — Human Review UI for Nutrition Proposals
```

Suggested distribution:

| Block | Task | Weight |
|---:|---|---:|
| 1 | Add proposal detail UI sections for payload and simulation | 25% |
| 2 | Render meal proposal review cards | 20% |
| 3 | Render DailyPlan build proposal review cards | 25% |
| 4 | Add safe review decisions without applying nutrition changes | 15% |
| 5 | E2E tests and documentation | 15% |

Expected result:

```txt
Humans can inspect AI/MCP proposals in the UI before any apply flow exists.
```