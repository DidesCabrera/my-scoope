# 0070 · Admin Operations Console planning

Date: 2026-07-04
Status: accepted
Related planning: `docs/10_active_cycles/admin_operations_console_cycle.md`
Related decisions:

```text
0053 · Admin Analytics strategic dashboard
0063 · Admin Analytics cycle closure
0064 · Admin Analytics independent shell
0069 · Admin Analytics mobile shell and filter drawer
```

## Decision

Create a future Django app named:

```text
admin_operations
```

It will be the staff-only operational companion to `admin_analytics`.

The boundary is:

```text
admin_analytics = observe, aggregate, summarize and alert.
admin_operations = act, review, configure and resolve.
Django Admin = legacy/raw technical admin for exceptional manual work.
```

## Rationale

Admin Analytics V1 gave My Scoope a strategic console that reads data across `accounts`,
`ai_assistant`, `notas`, `food_catalog` and `nutrition_solver`. The next internal product
need is not more measurement; it is a safe place for staff to act on operational issues.

Adding action buttons directly to `admin_analytics` would weaken the read-first guarantee
and make the strategic dashboard responsible for business mutations. A separate app keeps
risk lower and preserves a clear mental model:

```text
Analytics detects the problem.
Operations resolves the problem.
```

## Consequences

- `admin_analytics` should stay read-first.
- `admin_operations` may execute state-changing workflows, but only through guided actions.
- State-changing actions should require validation, confirmation and eventually audit logs.
- The existing Django Admin is not removed; it becomes legacy/raw technical admin.
- Future Analytics alerts may link to Operations routes, but should not execute actions.

## Initial implementation cycle

The planned patch cycle is OPS00-OPS08:

```text
OPS00 — Docs: Admin Operations planning
OPS01 — App shell and independent console base
OPS02 — Operational overview and action queues
OPS03 — Food Catalog operations
OPS04 — Accounts and credits operations
OPS05 — AI Assistant and proposal operations
OPS06 — Operations audit log foundation
OPS07 — Cross-links from Admin Analytics
OPS08 — UI polish and V1 closure
```

The recommended MVP is:

```text
OPS00
OPS01
OPS02
OPS03
OPS06
```

This lets My Scoope ship a useful operational console with at least one real workflow and
an audit foundation before financial or AI intervention workflows become broader.

## Migration note

OPS00 is documentation-only and requires no migration.

Future patches may require migrations if they introduce a dedicated operations audit model
or new operational state. Each implementation patch must explicitly state whether to run
`migrate`.
