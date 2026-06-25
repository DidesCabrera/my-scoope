# Apply UI Integration

## Purpose

This document records the UI integration for safely applying approved nutrition proposals in My Scoope.

This stage connects the internal safe apply commands to authenticated human UI actions.

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
Etapa 6 — Apply UI Integration
```

Stage distribution:

| Block | Task | Weight | Status |
|---:|---|---:|---|
| 1 | Create web routes/views for applying approved proposals | 20% | Completed |
| 2 | Add "Apply proposal" button in proposal detail | 20% | Completed |
| 3 | Show applied state and links to created objects | 25% | Completed |
| 4 | Protect UI against double apply and invalid states | 20% | Completed |
| 5 | Tests and documentation | 15% | Completed |

Total:

```txt
100% completed
```

---

## Product Flow

The final human flow is:

```txt
1. MCP creates a proposal.
2. User reviews the proposal in My Scoope.
3. User approves the proposal.
4. User applies the approved proposal.
5. System creates final nutrition objects.
6. Proposal becomes applied.
7. UI shows the created object link.
```

---

# Supported Apply Intents

The UI apply flow currently supports:

```txt
create_meal
create_dailyplan
```

Unsupported intents do not show an apply button.

Legacy or non-supported approved proposals show a safe non-applicable state.

---

# Web Entry Point

The web apply route is:

```txt
POST /app/proposals/<proposal_id>/apply/
```

Django URL name:

```txt
proposal_apply
```

This route is a human web action.

It is not exposed through MCP.

---

# Apply Dispatcher

The `proposal_apply` view dispatches by proposal intent:

```txt
create_meal      -> apply_approved_create_meal_proposal
create_dailyplan -> apply_approved_create_dailyplan_proposal
```

Unsupported intents are rejected safely.

Errors are shown through Django messages and redirect back to proposal detail.

---

# Proposal Detail UI

The proposal detail page now renders apply state through these partials:

```txt
notas/templates/notas/proposals/partials/review_apply_action.html
notas/templates/notas/proposals/partials/review_applied_result.html
notas/templates/notas/proposals/partials/review_actions.html
```

The intended visual state matrix is:

| Proposal state | Supported intent | UI behavior |
|---|---:|---|
| pending_review | yes/no | show approve/reject/cancel |
| approved | yes | show Apply proposal |
| approved | no | show approved but not automatically applicable |
| applied | yes/no | show applied state/result |
| rejected | yes/no | show closed review |
| cancelled | yes/no | show closed review |

---

# ViewModel Support

The proposal review UI is powered by:

```txt
notas/presentation/proposals/proposal_review_viewmodels.py
```

Important fields:

```txt
status.is_reviewable
status.is_approved
status.is_applied
payload.is_apply_supported
can_apply
applied_result
```

`can_apply` is true only when:

```txt
status = approved
intent is supported
applied_at is empty
```

`applied_result` is built from the applied audit event metadata.

---

# Applied Result Links

After apply, the UI can link to created objects.

For `create_meal`, audit metadata includes:

```txt
meal_id
meal_name
```

The UI shows:

```txt
Ver comida creada
```

For `create_dailyplan`, audit metadata includes:

```txt
dailyplan_id
dailyplan_name
```

The UI shows:

```txt
Ver DailyPlan creado
```

---

# Query Layer Support

Proposal detail includes audit events through:

```txt
get_proposal_detail
build_proposal_dto
```

The DTO exposes:

```txt
audit_events
applied_at
```

This lets the ViewModel build `applied_result`.

---

# Safety Rules

The UI and backend enforce:

```txt
pending_review cannot be applied
rejected cannot be applied
cancelled cannot be applied
already applied cannot be applied again
unsupported intents cannot be applied
private proposals from other users cannot be applied
```

The backend command layer remains the final authority.

The UI is helpful, but not trusted as the only protection.

---

# Double Apply Protection

Double apply is protected at command level.

If the user submits apply twice:

```txt
first request creates final objects
second request fails safely
no duplicate Meal is created
no duplicate DailyPlan is created
```

The proposal remains applied.

---

# Testing Policy

Tests in this stage protect product behavior, not exact copy.

Required tests protect:

```txt
state transitions
visibility of apply action
absence of apply action for invalid states
creation of final objects through web apply
double apply protection
ownership protection
applied result state
```

Avoid overly fragile tests for long copy or visual-only wording.

---

# Relevant Tests

```txt
notas/tests/test_proposal_views.py
notas/tests/test_proposal_review_viewmodels.py
notas/tests/test_apply_create_meal_proposal_command.py
notas/tests/test_apply_create_dailyplan_proposal_command.py
```

Recommended command:

```bash
python manage.py test notas.tests.test_proposal_views notas.tests.test_proposal_review_viewmodels
```

Broader regression command:

```bash
python manage.py test notas.tests.test_proposal_views notas.tests.test_proposal_review_viewmodels notas.tests.test_apply_create_meal_proposal_command notas.tests.test_apply_create_dailyplan_proposal_command
```

---

# MCP Boundary

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

Apply remains a human authenticated web action.

---

# Final Outcome

At the end of this stage:

```txt
Approved create_meal proposals can be applied from UI.
Approved create_dailyplan proposals can be applied from UI.
Applied proposals link to created objects.
Invalid states are protected.
Double apply does not duplicate objects.
MCP still cannot apply.
```

---

# Recommended Next Stage

The next natural stage is:

```txt
Etapa 7 — Proposal UX Polish and Audit Visibility
```

Suggested distribution:

| Block | Task | Weight |
|---:|---|---:|
| 1 | Improve proposal detail layout and visual hierarchy | 25% |
| 2 | Show audit timeline in proposal detail | 20% |
| 3 | Improve success/error messages after apply | 15% |
| 4 | Add direct navigation from applied proposal to object | 20% |
| 5 | Final tests and documentation | 20% |

Expected result:

```txt
Proposal review/apply feels like a polished product flow, not just a technical integration.
```