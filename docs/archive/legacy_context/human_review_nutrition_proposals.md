# Human Review UI for Nutrition Proposals

## Purpose

This document records the Human Review UI layer for AI/MCP nutrition proposals in My Scoope.

The goal of this stage is to let humans inspect nutrition proposals created by AI/MCP before any final nutrition object is created or modified.

This stage is focused on review, clarity and safety.

---

## Stage

This document records the completion of:

```txt
Etapa 4 — Human Review UI for Nutrition Proposals
```

Stage distribution:

| Block | Task | Weight | Status |
|---:|---|---:|---|
| 1 | Reinforce proposal detail read model / review ViewModel | 20% | Completed |
| 2 | Render `create_meal` proposals | 20% | Completed |
| 3 | Render `create_dailyplan` proposals | 25% | Completed |
| 4 | Add safe human review actions | 20% | Completed |
| 5 | Tests and documentation | 15% | Completed |

Total:

```txt
100% completed
```

---

## Product Boundary

This stage does not apply nutrition changes.

Approving a proposal does not:

```txt
create final Meal records
create final MealFood records
create final DailyPlan records
modify existing DailyPlans
apply proposed payloads
```

This boundary is intentional.

At this stage:

```txt
AI/MCP proposes.
Human reviews.
Human approves, rejects or cancels.
Nothing is applied yet.
```

---

## Supported Proposal Intents

The review UI currently supports rich proposal payloads for:

```txt
create_meal
create_dailyplan
```

Legacy or non-classified proposals are still shown safely, but they do not render rich nutrition review cards.

---

# Proposal Review ViewModel

The review ViewModel lives in:

```txt
notas/presentation/proposals/proposal_review_viewmodels.py
```

Main function:

```txt
build_proposal_review_vm
```

It converts the proposal dictionary from the read layer into a template-friendly structure.

It exposes:

```txt
proposal_id
title
summary
dailyplan_id
dailyplan_name
created_by_username
reviewed_by_username
status
payload.intent
payload.is_create_meal
payload.is_create_dailyplan
payload.targets
payload.meal
payload.dailyplan
```

The template accesses it through:

```txt
vm.content.proposal_review
```

This follows the current `BaseVM.as_context()` convention.

---

# Proposal Detail Page

The proposal detail view now sends both:

```txt
proposal
proposal_review
```

inside the content VM.

The raw proposal remains available for backwards compatibility, while the new review UI uses the structured `proposal_review` object.

---

# create_meal Review UI

For proposal payloads with:

```json
{
  "intent": "create_meal"
}
```

the UI renders:

```txt
meal name
food list
food quantity
food protein/carbs/fat
food total kcal
meal total kcal
meal protein
meal carbs
meal fat
meal ppk when available
```

The partial lives in:

```txt
notas/templates/notas/proposals/partials/review_create_meal.html
```

Expected user-facing result:

```txt
A human can review a proposed meal without reading raw JSON.
```

---

# create_dailyplan Review UI

For proposal payloads with:

```json
{
  "intent": "create_dailyplan"
}
```

the UI renders:

```txt
proposed DailyPlan name
DailyPlan total KPIs
proposed meals
meal hour
meal note
meal name
food list per meal
food quantity
food protein/carbs/fat
food total kcal
meal-level KPIs
dailyplan-level KPIs
```

The partial lives in:

```txt
notas/templates/notas/proposals/partials/review_create_dailyplan.html
```

Expected user-facing result:

```txt
A human can review a complete AI/MCP DailyPlan proposal without reading raw JSON.
```

---

# Human Review Actions

The review actions partial lives in:

```txt
notas/templates/notas/proposals/partials/review_actions.html
```

For reviewable proposals, the UI shows:

```txt
Approve proposal
Reject proposal
Cancel proposal
```

In Spanish UI copy:

```txt
Aprobar propuesta
Rechazar propuesta
Cancelar propuesta
```

For final proposals, the UI shows a closed-review message.

The supported state transitions are:

```txt
pending_review -> approved
pending_review -> rejected
pending_review -> cancelled
```

These actions only change proposal review state.

They do not apply the proposal payload.

---

# Safe Review Boundary

The review actions are intentionally safe.

Approving a `create_meal` proposal does not create a final `Meal`.

Approving a `create_dailyplan` proposal does not create a final `DailyPlan` or final `Meal`.

Rejecting or cancelling a proposal also does not create or modify final nutrition objects.

This preserves the boundary between:

```txt
review
```

and:

```txt
apply
```

---

# Current Templates

Relevant templates:

```txt
notas/templates/notas/proposals/detail.html
notas/templates/notas/proposals/partials/review_create_meal.html
notas/templates/notas/proposals/partials/review_create_dailyplan.html
notas/templates/notas/proposals/partials/review_actions.html
```

---

# Current Tests

Relevant tests:

```txt
notas/tests/test_proposal_review_viewmodels.py
notas/tests/test_proposal_views.py
```

The tests cover:

```txt
review ViewModel for create_meal
review ViewModel for create_dailyplan
proposal detail displays create_meal review
proposal detail displays create_dailyplan review
proposal detail displays review actions
final proposals show closed review message
approve create_meal does not create Meal
approve create_dailyplan does not create DailyPlan or Meal
reject create_dailyplan does not create DailyPlan or Meal
private proposals remain protected
legacy validation display remains available
```

Recommended command:

```bash
python manage.py test notas.tests.test_proposal_review_viewmodels notas.tests.test_proposal_views
```

Broader proposal regression command:

```bash
python manage.py test notas.tests.test_proposal_review_viewmodels notas.tests.test_proposal_views notas.tests.test_create_validated_meal_proposal_command notas.tests.test_create_validated_dailyplan_build_proposal_command
```

---

# Relationship with MCP Stages

This stage builds on previous MCP proposal stages:

```txt
Etapa 1 — Rich proposal payload contracts
Etapa 2 — MCP meal proposals
Etapa 3 — MCP DailyPlan build proposals
Etapa 4 — Human Review UI
```

The UI now makes MCP-created proposals readable and reviewable by humans.

---

# Recommended Next Stage

The next natural stage is:

```txt
Etapa 5 — Safe Apply Flow for Approved Proposals
```

Suggested distribution:

| Block | Task | Weight |
|---:|---|---:|
| 1 | Define apply contracts for `create_meal` | 20% |
| 2 | Apply approved `create_meal` proposal into final Meal objects | 25% |
| 3 | Define apply contracts for `create_dailyplan` | 20% |
| 4 | Apply approved `create_dailyplan` proposal into final DailyPlan/Meal objects | 25% |
| 5 | E2E tests and documentation | 10% |

Expected result:

```txt
Approved proposals can be safely applied by a human action.
```

The apply flow should remain unavailable to MCP.

MCP may propose. Humans review and apply.