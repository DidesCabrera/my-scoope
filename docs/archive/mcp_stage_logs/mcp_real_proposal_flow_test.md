# MCP Real Proposal Flow Test

## Purpose

This document records the real MCP flow for creating a reviewable `NutritionProposal` in My Scoope.

The tested flow is:

```txt
MCP Inspector
  -> FastMCP protocol wrapper
  -> dispatch_tool_call
  -> MyscoopeAPIClient
  -> Django API Adapter
  -> Internal AI Tools
  -> NutritionProposal
```

The purpose of this validation is to confirm that MCP can safely interact with My Scoope through controlled internal tools, without directly mutating final nutrition data.

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

MCP Inspector must also be running:

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

## Generic Test Flow

The following steps describe the generic flow. The example `dailyplan_id` is illustrative.

For the real validated result, see the section:

```txt
Real E2E Validation Result - 2026-05-07
```

---

## Step 1: Read DailyPlan

Tool:

```txt
read_dailyplan
```

Arguments:

```json
{
  "dailyplan_id": 123
}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "dailyplan": {}
  },
  "error": null
}
```

This confirms that MCP can read a DailyPlan through the protocol wrapper and API adapter.

---

## Step 2: Compare DailyPlan to Targets

Tool:

```txt
compare_dailyplan_to_targets
```

Arguments:

```json
{
  "dailyplan_id": 123,
  "targets": {
    "protein": 190,
    "total_kcal": 2800
  },
  "tolerances": {
    "protein": 10,
    "total_kcal": 100
  }
}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "validation": {}
  },
  "error": null
}
```

This confirms that MCP can ask My Scoope to validate a DailyPlan against explicit nutrition targets.

Supported target metrics are:

```txt
total_kcal
protein
carbs
fat
ppk
```

---

## Step 3: Create Validated DailyPlan Proposal

Tool:

```txt
create_validated_dailyplan_proposal
```

Arguments:

```json
{
  "dailyplan_id": 123,
  "title": "Propuesta MCP - Ajuste de proteína",
  "summary": "Propuesta creada desde MCP Inspector para acercar el plan a los objetivos definidos.",
  "targets": {
    "protein": 190,
    "total_kcal": 2800
  },
  "tolerances": {
    "protein": 10,
    "total_kcal": 100
  },
  "proposed_payload": {
    "intent": "adjust_dailyplan_to_targets",
    "suggested_changes": []
  }
}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "proposal": {}
  },
  "error": null
}
```

This confirms that MCP can create a reviewable proposal, without applying changes directly to the DailyPlan.

---

## Step 4: Read Created Proposal

Tool:

```txt
read_proposal
```

Arguments:

```json
{
  "proposal_id": 1
}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "proposal": {}
  },
  "error": null
}
```

This confirms that the created proposal can be retrieved through MCP.

---

## Step 5: List User Proposals

Tool:

```txt
list_user_proposals
```

Arguments:

```json
{}
```

Expected successful shape:

```json
{
  "ok": true,
  "data": {
    "proposals": []
  },
  "error": null
}
```

This confirms that the created proposal appears in the authenticated user's proposal list.

---

## Verification in My Scoope

Open:

```txt
http://127.0.0.1:8000/app/proposals/
```

Expected result:

```txt
A proposal created from MCP appears in the proposal list.
```

The proposal should remain reviewable and pending human approval.

---

## Product Boundary

This flow creates a reviewable proposal.

It does not:

```txt
approve the proposal
apply the proposal
modify the final DailyPlan
expose apply tools through MCP
```

Final application remains inside My Scoope's authenticated human review flow.

This boundary is intentional.

MCP can propose changes, but it should not directly mutate nutrition plans.

---

## Possible Authentication Boundary

If the MCP call returns an authentication-related error, the MCP runtime may still be correctly wired.

That means the next required stage would be:

```txt
Internal API Auth for MCP
```

The expected future solution is an internal token-based auth path from MCP to the Django API Adapter.

---

# Real E2E Validation Result - 2026-05-07

This section records the successful real MCP Inspector validation performed against the local My Scoope runtime.

---

## Tested DailyPlan

DailyPlan:

```json
{
  "dailyplan_id": 128,
  "dailyplan_name": "Menú Dia Entrenamiento"
}
```

---

## Targets Used

```json
{
  "protein": 190,
  "total_kcal": 2800
}
```

---

## Validation Result

Tool:

```txt
compare_dailyplan_to_targets
```

Result:

```json
{
  "ok": true,
  "data": {
    "validation": {
      "dailyplan_id": 128,
      "dailyplan_name": "Menú Dia Entrenamiento",
      "targets": {
        "protein": 190,
        "total_kcal": 2800
      },
      "actual": {
        "protein": 125.6,
        "total_kcal": 1925.2800000000002
      },
      "delta": {
        "protein": -64.4,
        "total_kcal": -874.7199999999998
      },
      "tolerances": {
        "protein": 10,
        "total_kcal": 100
      },
      "within_tolerance": false,
      "metrics": [
        {
          "metric": "protein",
          "target": 190,
          "actual": 125.6,
          "delta": -64.4,
          "tolerance": 10,
          "within_tolerance": false,
          "status": "under_target"
        },
        {
          "metric": "total_kcal",
          "target": 2800,
          "actual": 1925.2800000000002,
          "delta": -874.7199999999998,
          "tolerance": 100,
          "within_tolerance": false,
          "status": "under_target"
        }
      ]
    }
  },
  "error": null
}
```

Validation summary:

```txt
protein: under target by 64.4 g
total_kcal: under target by 874.72 kcal
within_tolerance: false
```

---

## Proposal Creation Result

Tool:

```txt
create_validated_dailyplan_proposal
```

Result:

```json
{
  "ok": true,
  "data": {
    "proposal": {
      "id": 1,
      "dailyplan_id": 128,
      "dailyplan_name": "Menú Dia Entrenamiento",
      "created_by_id": 8,
      "created_by_username": "felipe",
      "reviewed_by_id": null,
      "reviewed_by_username": null,
      "status": "pending_review",
      "source": "ai",
      "title": "Propuesta MCP - Ajuste a objetivos de entrenamiento",
      "summary": "",
      "targets": {
        "protein": 190,
        "total_kcal": 2800
      },
      "current_snapshot": {
        "dailyplan_id": 128,
        "dailyplan_name": "Menú Dia Entrenamiento",
        "actual": {
          "protein": 125.6,
          "total_kcal": 1925.2800000000002
        }
      },
      "proposed_payload": {
        "intent": "adjust_dailyplan_to_targets",
        "suggested_changes": []
      },
      "validation_summary": {
        "dailyplan_id": 128,
        "dailyplan_name": "Menú Dia Entrenamiento",
        "targets": {
          "protein": 190,
          "total_kcal": 2800
        },
        "actual": {
          "protein": 125.6,
          "total_kcal": 1925.2800000000002
        },
        "delta": {
          "protein": -64.4,
          "total_kcal": -874.7199999999998
        },
        "tolerances": {
          "protein": 10,
          "total_kcal": 100
        },
        "within_tolerance": false
      },
      "is_reviewable": true,
      "is_final": false,
      "created_at": "2026-05-07T00:30:59.651055+00:00",
      "reviewed_at": null
    }
  },
  "error": null
}
```

Confirmed result:

```txt
Proposal created successfully.
Proposal id: 1
Status: pending_review
Reviewable: true
Final: false
```

---

## Proposal Read Verification

Tool:

```txt
read_proposal
```

Arguments:

```json
{
  "proposal_id": 1
}
```

Result:

```json
{
  "ok": true,
  "data": {
    "proposal": {
      "id": 1,
      "dailyplan_id": 128,
      "dailyplan_name": "Menú Dia Entrenamiento",
      "created_by_id": 8,
      "created_by_username": "felipe",
      "reviewed_by_id": null,
      "reviewed_by_username": null,
      "status": "pending_review",
      "source": "ai",
      "title": "Propuesta MCP - Ajuste a objetivos de entrenamiento",
      "summary": "",
      "targets": {
        "protein": 190,
        "total_kcal": 2800
      },
      "current_snapshot": {
        "dailyplan_id": 128,
        "dailyplan_name": "Menú Dia Entrenamiento",
        "actual": {
          "protein": 125.6,
          "total_kcal": 1925.2800000000002
        }
      },
      "proposed_payload": {
        "intent": "adjust_dailyplan_to_targets",
        "suggested_changes": []
      },
      "is_reviewable": true,
      "is_final": false,
      "created_at": "2026-05-07T00:30:59.651055+00:00",
      "reviewed_at": null
    }
  },
  "error": null
}
```

Confirmed result:

```txt
The created proposal can be read through MCP.
```

---

## Proposal List Verification

Tool:

```txt
list_user_proposals
```

Arguments:

```json
{}
```

Result:

```json
{
  "ok": true,
  "data": {
    "proposals": [
      {
        "id": 1,
        "dailyplan_id": 128,
        "dailyplan_name": "Menú Dia Entrenamiento",
        "created_by_id": 8,
        "created_by_username": "felipe",
        "reviewed_by_id": null,
        "reviewed_by_username": null,
        "status": "pending_review",
        "source": "ai",
        "title": "Propuesta MCP - Ajuste a objetivos de entrenamiento",
        "summary": "",
        "is_reviewable": true,
        "is_final": false,
        "created_at": "2026-05-07T00:30:59.651055+00:00",
        "reviewed_at": null
      }
    ]
  },
  "error": null
}
```

Confirmed result:

```txt
The created proposal appears in the authenticated user's proposal list.
```

---

## MCP Inspector Notes

During this validation, MCP Inspector did not make it easy to manually fill optional object parameters such as:

```txt
tolerances
proposed_payload
```

This did not block the flow because the backend applied safe defaults.

Default tolerances used:

```json
{
  "protein": 10,
  "total_kcal": 100
}
```

Default proposed payload used:

```json
{
  "intent": "adjust_dailyplan_to_targets",
  "suggested_changes": []
}
```

This behavior is acceptable for the current validation stage.

---

## Final Validation Outcome

The real MCP E2E flow was validated successfully:

```txt
MCP Inspector
  -> FastMCP protocol wrapper
  -> dispatch_tool_call
  -> MyscoopeAPIClient
  -> Django API Adapter
  -> Internal AI Tools
  -> NutritionProposal
```

Validated capabilities:

```txt
read_dailyplan: ok
compare_dailyplan_to_targets: ok
create_validated_dailyplan_proposal: ok
read_proposal: ok
list_user_proposals: ok
```

Product safety boundary confirmed:

```txt
MCP can read DailyPlans.
MCP can validate DailyPlans against targets.
MCP can create reviewable proposals.
MCP cannot approve proposals.
MCP cannot apply proposals.
MCP cannot directly mutate DailyPlans.
```

---

## Stage Completion

The validation stage was divided as follows:

| Block | Task | Weight | Status |
|---:|---|---:|---|
| 1 | Prepare local E2E environment | 20% | Completed |
| 2 | Test `list_user_proposals` with real auth | 20% | Completed |
| 3 | Test `read_dailyplan` and `compare_dailyplan_to_targets` | 20% | Completed |
| 4 | Create real proposal from MCP | 25% | Completed |
| 5 | Document final result and troubleshooting | 15% | Completed |

Total:

```txt
100% completed
```

---

## Follow-up Improvements

These improvements are intentionally left outside this validation stage:

1. Set proposal source to `mcp` when created from the MCP protocol wrapper.
2. Improve MCP Inspector object-field ergonomics by tightening JSON schemas for object properties.
3. Add a richer `proposed_payload` generator in a future optimization/proposal-planning layer.
4. Add UI review screens for inspecting `validation_summary`, `current_snapshot`, and `proposed_payload`.
5. Later expose only safe proposal review actions, if needed, while keeping apply actions inside the authenticated human review flow.

---

## Recommended Next Stage

The next natural stage is:

```txt
MCP Contract Refinement
```

Suggested focus:

```txt
source=mcp
better schemas for optional object fields
more expressive proposed_payload
human review UI for proposals
proposal review endpoints kept outside MCP apply path
```