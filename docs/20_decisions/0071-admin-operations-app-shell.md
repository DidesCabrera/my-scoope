# 0071 · Admin Operations app shell

Date: 2026-07-04
Status: accepted
Related planning: `docs/10_active_cycles/admin_operations_console_cycle.md`
Related decisions:

```text
0070 · Admin Operations Console planning
0064 · Admin Analytics independent shell
0069 · Admin Analytics mobile shell and filter drawer
```

## Decision

Implement OPS01 by creating the physical Django app:

```text
admin_operations
```

Expose the first staff-only route at:

```text
/staff/operations/
```

The initial screen is an independent operational console shell with placeholders for the
future operational modules.

## Rationale

The project now needs a product operations surface distinct from both Admin Analytics and
Django Admin. Creating the app shell first gives the cycle a stable route, visual frame,
access pattern and test boundary before any state-changing workflow is added.

The shell intentionally reuses Admin Analytics visual primitives while adding a small
`admin_operations.css` layer. This avoids premature extraction of a shared `staff_console`
package while keeping the UI aligned.

## Scope included in OPS01

```text
- Register `admin_operations` in Django settings.
- Add `/staff/operations/` URL routing.
- Protect the overview with `staff_member_required`.
- Add an independent base template, sidebar navigation and overview page.
- Add placeholders for Food Catalog, Accounts & Credits, AI Assistant and Audit Log.
- Add access/shell tests for anonymous, non-staff and staff users.
```

## Scope excluded

```text
- No operational mutations yet.
- No audit model yet.
- No Food Catalog approval/rejection workflow yet.
- No account/credit adjustment flow yet.
- No cross-links from Admin Analytics yet.
```

## Migration note

OPS01 creates no models and requires no migration.
