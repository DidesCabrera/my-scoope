# Admin Operations Console Cycle

Status: completed
Date: 2026-07-04
Owner: Product / Internal Operations
App target: `admin_operations`
Related console: `admin_analytics`

## Context

Admin Analytics V1 established the strategic internal console for My Scoope. Its
responsibility is intentionally read-first: observe, aggregate, summarize and alert across
`accounts`, `ai_assistant`, `notas`, `food_catalog` and `nutrition_solver`.

That separation makes a second need visible: My Scoope also needs an operational console
where staff users can act on the signals surfaced by Analytics. These actions should not be
added to `admin_analytics`, because mixing measurement and intervention would blur the
product boundary and increase risk.

## Core decision

Create a separate Django app:

```text
admin_operations
```

This app will become the staff-only operational console for guided administrative actions.

The operating rule is:

```text
admin_analytics detects what is happening.
admin_operations lets staff resolve it.
Django Admin remains raw/legacy technical admin.
```

## Console roles

| Surface | Role | Nature |
| --- | --- | --- |
| `admin_analytics` | Strategic dashboard | Read-first metrics, health signals, alerts |
| `admin_operations` | Operational console | Guided actions, review queues, configuration and remediation |
| Django Admin | Legacy/raw admin | Emergency/manual technical editing and debugging |

## Non-goals

The first cycle should not try to replace every Django Admin screen. It should focus on
safe, high-value operational workflows with clear validations and auditability.

Do not build broad CRUD by default. Prefer guided actions that express business intent,
for example:

```text
approve catalog candidate
reject catalog candidate
adjust user credits with reason
release stuck reservation
review AI proposal
block or unblock AI access
```

## Design principles

1. **Action-oriented, not analytical**
   - It may show counts and queues, but its purpose is intervention.

2. **Staff-only by default**
   - All routes must require authenticated staff users.

3. **Audit-first**
   - Every state-changing operation should eventually capture actor, entity, action,
     previous state, new state, reason and timestamp.

4. **Domain validation over raw editing**
   - Use application services/commands instead of direct model mutation where available.

5. **Confirm destructive or financial actions**
   - Credit changes, unblocking, rejection, disabling and reservation release require clear
     confirmation and a reason.

6. **Link from Analytics, act in Operations**
   - Analytics may link to operational queues, but should not execute actions.

## Suggested URL structure

```text
/staff/operations/
/staff/operations/users/
/staff/operations/accounts/
/staff/operations/ai-assistant/
/staff/operations/food-catalog/
/staff/operations/nutrition-solver/
/staff/operations/proposals/
/staff/operations/audit-log/
```

## V1 cycle

### OPS00 — Docs: Admin Operations planning

Record the architectural decision and implementation plan.

Scope:

```text
- Define `admin_operations` as the operational companion to `admin_analytics`.
- Define console responsibilities and boundaries.
- Mark Django Admin as legacy/raw technical admin, not product operations UI.
- Plan the first patch cycle.
```

### OPS01 — App shell and independent console base

Status: implemented in `docs/decisions/0071-admin-operations-app-shell.md`.

Create the app shell.

Scope:

```text
- Create Django app `admin_operations`.
- Register app in settings.
- Add `/staff/operations/` route.
- Staff-only access guard.
- Independent shell aligned with Admin Analytics visual system.
- Navigation placeholders for operational modules.
- Basic tests for staff/non-staff access.
```

Migration expectation: no migration.

Implementation note:

```text
- Shell lives at /staff/operations/.
- Visual base reuses Admin Analytics primitives plus admin_operations.css.
- Navigation modules are placeholders until OPS02+ adds real queues/actions.
```

### OPS02 — Operational overview and action queues

Status: implemented in `docs/decisions/0072-admin-operations-operational-overview.md`.

Create the first read/action overview.

Scope:

```text
- Pending catalog candidates.
- Catalog foods requiring review before publication/readiness.
- AI usage events with error/block status in the last 7 days.
- AI/MCP NutritionProposal records pending review.
- Wallets with reserved credits as the first detectable account/credit queue.
- Recent operational warnings derived from those queues.
- Disabled action labels that prepare the module-specific workflows.
```

Migration expectation: no migration.

Implementation note:

```text
- OPS02 remains read/action-prioritization only.
- It does not approve, reject, release, adjust or mutate domain records.
- Queue actions remain disabled until OPS03/OPS04/OPS05/OPS06 add safe workflows.
```

### OPS03 — Food Catalog operations

Status: implemented in `docs/decisions/0073-admin-operations-food-catalog-workflow.md`.

Build the first domain-specific operational workflow.

Scope:

```text
- List curation candidates.
- Detail view for a candidate.
- Approve / reject with reason.
- Mark follow-up needed.
- Review foods requiring curation attention.
- Keep actions inside Food Catalog service/command boundaries where possible.
```

Migration expectation: no migration.

Implementation note:

```text
- /staff/operations/food-catalog/ is now enabled.
- Candidate actions require a reason and append an operational note to the candidate.
- CatalogFood actions reuse transition_catalog_food_status.
- OPS03 does not create CatalogFood from candidates and does not write notas.Food snapshots.
```

### OPS04 — Accounts and credits operations

Status: implemented in `docs/decisions/0074-admin-operations-accounts-credits-workflow.md`.

Create safe commercial/account interventions.

Scope:

```text
- Search users/accounts.
- View wallet and credit ledger by user.
- Manual credit adjustment with required reason.
- Release stuck reserved credits if supported.
- View active plan/subscription context.
- Prevent silent financial mutations.
```

Migration expectation: no migration. OPS04 reuses `CreditWallet` and append-only
`CreditLedger`; formal audit consolidation remains in OPS06.

Implementation note:

```text
- /staff/operations/accounts/ is now enabled.
- Manual adjustments append CreditLedger.Kind.ADJUSTMENT.
- Reservation releases reuse release_account_credit_reservation.
- Balance adjustments require reason and cannot create invalid reserved/balance state.
- Staff actor metadata is stored in ledger metadata until OPS06 formalizes audit log.
```

### OPS05 — AI Assistant and proposal operations

Status: implemented in `docs/decisions/0075-admin-operations-ai-assistant-workflow.md`.

Create safe AI operational workflows.

Scope:

```text
- Review recent AI errors/blocked events.
- Open related user/proposal context.
- Review NutritionProposal operational status.
- Administrative status transitions where appropriate.
- Block/unblock AI access only if the account/AI quota model supports it.
```

Migration expectation: no migration. OPS05 reuses `AIUsageEvent`, `AIUserCreditQuota`,
`AICreditLedger`, `NutritionProposal` and `NutritionProposalAuditEvent`.

Implementation note:

```text
- /staff/operations/ai-assistant/ is now enabled.
- AIUsageEvent review writes metadata.admin_operations instead of rewriting usage status.
- AI/MCP proposal approval/rejection requires reason and writes NutritionProposalAuditEvent.
- Quota block/unblock toggles hard_blocked and appends a zero-credit AICreditLedger trace.
- OPS05 does not apply proposal payloads or execute LLM tools.
```

### OPS06 — Operations audit log foundation

Status: implemented in `docs/decisions/0076-admin-operations-audit-log-foundation.md`.

Introduce consolidated auditability for operational actions.

Scope:

```text
- Create `AdminOperationAuditEvent` in `admin_operations`.
- Record actor, action, target app/model/id, previous state, new state, reason and metadata.
- Expose `/staff/operations/audit-log/` as a staff-only audit screen.
- Wire audit writes into Food Catalog, Accounts/Credits and AI Assistant mutations.
- Add tests proving state-changing actions write audit entries.
```

Migration expectation: yes. OPS06 creates `AdminOperationAuditEvent`.

Implementation note:

```text
- The audit model is append-only and blocks update/delete at model level.
- Domain-specific ledgers/audit records remain authoritative inside their own domains.
- AdminOperationAuditEvent is the transversal staff-action log for Admin Operations.
```

### OPS07 — Cross-links from Admin Analytics

Status: implemented in `docs/decisions/0077-admin-analytics-operations-cross-links.md`.

Connect signals to actions without mixing responsibilities.

Scope:

```text
- Add "Open in Operations" links from relevant Analytics alerts/sections.
- Preserve `admin_analytics` as read-first.
- Deep-link to operational queues with filters when possible.
```

Migration expectation: no migration.

Implementation note:

```text
- Analytics pages now render a bridge card to the matching Operations workflow.
- The Analytics sidebar includes an Admin Operations shortcut.
- The links are GET-only navigation; all mutations remain in admin_operations.
```

### OPS08 — UI polish and V1 closure

Status: implemented in `docs/decisions/0078-admin-operations-v1-closure.md`.

Close the first operational console cycle.

Scope:

```text
- Mobile polish.
- Empty states.
- Confirmation flows.
- Documentation update.
- Final access tests and smoke checks.
```

Migration expectation: no migration.

Implementation note:

```text
- /staff/operations/ now includes an OPS08 V1 closure card.
- Mutating forms opt into data-admin-operations-confirm.
- Confirmation is client-side UX; server validations and audit writes remain authoritative.
- Tables gain mobile card behavior through data-label attributes.
- The OPS00-OPS08 cycle is closed; future work should start a new cycle.
```

## V1 delivered scope

The completed first release includes:

```text
OPS00
OPS01
OPS02
OPS03
OPS04
OPS05
OPS06
OPS07
OPS08
```

This creates the operational shell, action queues, Food Catalog operations, Accounts &
Credits operations, AI Assistant/proposal operations, transversal audit logging,
Analytics-to-Operations navigation and V1 UI/confirmation polish.

## Resolved questions in V1

```text
- `admin_operations` reuses Admin Analytics visual primitives plus its own CSS layer.
- OPS06 created a dedicated AdminOperationAuditEvent model for transversal operational audit.
- V1 financial actions are limited to reason-required credit adjustments and reservation releases.
- Food Catalog was the first workflow because curation candidates already existed.
- Fine-grained permissions remain future work; V1 uses is_staff.
```

## Success criteria for V1

```text
- Staff users have a separate operational console at `/staff/operations/`.
- The console is not a raw Django Admin replacement.
- Multiple real operational queues can be resolved from the UI.
- State-changing actions are guided, confirmed and auditable.
- Admin Analytics remains read-first and links to Operations when intervention is needed.
```
