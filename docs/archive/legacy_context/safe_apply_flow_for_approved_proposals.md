# Safe Apply Flow for Approved Proposals

## Purpose

This document records the safe apply flow for approved nutrition proposals in My Scoope.

This stage converts approved AI/MCP proposals into real nutrition objects, but only through authenticated human actions.

The safety boundary remains:

```txt
MCP / AI proposes.
Human reviews.
Human approves.
Human applies.
System creates final objects.
```

MCP does not expose apply tools.

---

## Stage

This document records the completion of:

```txt
Etapa 5 — Safe Apply Flow for Approved Proposals
```

Stage distribution:

| Block | Task | Weight | Status |
|---:|---|---:|---|
| 1 | Define apply contracts for `create_meal` | 20% | Completed |
| 2 | Apply approved `create_meal` proposal into real Meal objects | 25% | Completed |
| 3 | Define apply contracts for `create_dailyplan` | 20% | Completed |
| 4 | Apply approved `create_dailyplan` proposal into real DailyPlan/snapshot objects | 25% | Completed |
| 5 | E2E tests and documentation | 10% | Completed |

Total:

```txt
100% completed
```

---

## Product Boundary

Apply is intentionally separate from approve.

Approving a proposal means:

```txt
A human accepted the proposal conceptually.
```

Applying a proposal means:

```txt
A human chose to create final nutrition objects from the approved proposal.
```

This separation avoids accidental writes.

---

# Supported Apply Intents

The safe apply flow currently supports:

```txt
create_meal
create_dailyplan
```

Other intents, including legacy adjustment proposals, remain outside this rich apply flow unless routed through their own explicit applicator.

---

# Apply Contract Layer

The apply contract lives in:

```txt
notas/application/dto/proposal_apply.py
```

It exposes:

```txt
build_create_meal_apply_plan
build_create_dailyplan_apply_plan
```

These functions validate and normalize approved proposals into serializable apply plans.

They do not create database objects.

---

## create_meal Apply Contract

A valid `create_meal` apply plan requires:

```txt
proposal.status = approved
proposal.proposed_payload.intent = create_meal
meal name exists
food items are valid
food quantities are positive
```

It returns:

```txt
proposal_id
intent
meal.name
meal.foods[]
```

The contract does not create a `Meal`.

---

## create_dailyplan Apply Contract

A valid `create_dailyplan` apply plan requires:

```txt
proposal.status = approved
proposal.proposed_payload.intent = create_dailyplan
dailyplan name exists
proposed meals are valid
food items are valid
food quantities are positive
hours are valid when provided
```

It returns:

```txt
proposal_id
intent
dailyplan.name
dailyplan.meals[]
```

The contract does not create a `DailyPlan`, `Meal`, `MealFood`, or `DailyPlanMeal`.

---

# Apply Command Layer

The apply command layer lives in:

```txt
notas/application/services/commands/proposal_commands.py
```

Relevant commands:

```txt
apply_approved_create_meal_proposal
apply_approved_create_dailyplan_proposal
```

Both commands require:

```txt
authenticated user
proposal owned by the user through DailyPlan context
proposal.status = approved
proposal not already applied
valid proposal payload
readable foods
```

---

# Applying create_meal

The command:

```txt
apply_approved_create_meal_proposal
```

creates:

```txt
1 real Meal
N real MealFood rows
```

It does not:

```txt
create a DailyPlan
create a DailyPlanMeal
attach the Meal to any DailyPlan
modify the context DailyPlan
```

The created Meal is:

```txt
created_by = applying user
is_public = false
is_draft = false
pending_dailyplan = null
```

This matches the product decision:

```txt
A create_meal proposal creates a reusable Meal in the user's library.
The user may later attach it to a DailyPlan manually.
```

---

# Applying create_dailyplan

The command:

```txt
apply_approved_create_dailyplan_proposal
```

creates:

```txt
1 real DailyPlan
N snapshot Meals
N DailyPlanMeal rows
N MealFood rows
```

It does not:

```txt
modify the context DailyPlan
create reusable library Meals for the proposed meals
copy targets/config from the context DailyPlan
leave the new DailyPlan as draft
```

The created DailyPlan is:

```txt
created_by = applying user
is_public = false
is_draft = false
source = proposal.source
```

The proposed meals become snapshot Meals attached to the new DailyPlan through `DailyPlanMeal`.

This matches the product decision:

```txt
A create_dailyplan proposal creates a new DailyPlan in the user's library.
Its meals are snapshots, not reusable Meals.
```

---

# Source / Provenance

`DailyPlan` has a `source` field.

Supported sources:

```txt
manual
ai
system
mcp
```

When a `create_dailyplan` proposal is applied, the resulting DailyPlan stores:

```txt
source = proposal.source
```

This preserves whether the proposal came from AI/MCP/system/manual flows.

---

# Audit Events

Apply commands create an audit event with:

```txt
action = applied
status_before = approved
status_after = applied
actor = applying user
metadata with created object IDs
```

For `create_meal`, metadata includes:

```txt
intent
meal_id
meal_name
foods[]
```

For `create_dailyplan`, metadata includes:

```txt
intent
dailyplan_id
dailyplan_name
source
meals[]
```

---

# Safety Rules

The safe apply flow enforces:

```txt
pending_review cannot be applied
rejected cannot be applied
cancelled cannot be applied
already applied cannot be applied again
private proposals from other users cannot be applied
foods from other users cannot be used
system foods are allowed
user-owned foods are allowed
```

---

# MCP Boundary

Apply tools are not exposed to MCP.

MCP can:

```txt
read
validate
propose
```

MCP cannot:

```txt
approve
reject
cancel
apply
```

The apply flow must remain a human authenticated web action.

---

# Relevant Modules

```txt
notas/application/dto/proposal_apply.py
notas/application/services/commands/proposal_commands.py
notas/application/dto/proposal_payloads.py
notas/application/validation/proposal_payload_validators.py
notas/application/queries/read_boundaries.py
notas/domain/models.py
```

---

# Relevant Tests

```txt
notas/tests/test_proposal_apply_dto.py
notas/tests/test_apply_create_meal_proposal_command.py
notas/tests/test_apply_create_dailyplan_proposal_command.py
notas/tests/test_proposal_views.py
```

Recommended command:

```bash
python manage.py test notas.tests.test_proposal_apply_dto notas.tests.test_apply_create_meal_proposal_command notas.tests.test_apply_create_dailyplan_proposal_command
```

Broader regression command:

```bash
python manage.py test notas.tests.test_proposal_apply_dto notas.tests.test_apply_create_meal_proposal_command notas.tests.test_apply_create_dailyplan_proposal_command notas.tests.test_proposal_views mcp_server/tests
```

---

# Final Outcome

At the end of this stage:

```txt
AI/MCP can create reviewable proposals.
Humans can review proposals in UI.
Humans can approve proposals.
Humans can apply approved proposals.
create_meal creates a real Meal.
create_dailyplan creates a real DailyPlan with snapshot meals.
MCP still cannot apply proposals.
```

---

# Recommended Next Stage

The next natural stage is:

```txt
Etapa 6 — Apply UI Integration
```

Suggested distribution:

| Block | Task | Weight |
|---:|---|---:|
| 1 | Add apply button for approved `create_meal` proposals | 20% |
| 2 | Add apply button for approved `create_dailyplan` proposals | 20% |
| 3 | Add success states and links to created objects | 25% |
| 4 | Add protection against repeated apply in UI | 20% |
| 5 | E2E tests and documentation | 15% |

Expected result:

```txt
Approved proposals can be applied from the proposal detail page.
After apply, the UI links to the created Meal or DailyPlan.
```