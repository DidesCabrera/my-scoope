# 0064 · Admin Analytics independent shell

Status: accepted
Date: 2026-07-04

## Context

After closing ADM00-ADM10, the strategic dashboard was accessible at `/staff/analytics/`,
but it still extended `notas/base.html`. That made the dashboard inherit the normal user
application shell: sidebar, header, user-account navigation and broad CSS from the
nutrition product experience.

This created two problems:

```text
- Admin Analytics visually behaved like a subsection of the user product.
- Admin Analytics styles could collide with existing My Scoope application styles.
```

The intended product boundary is different: Admin Analytics is an internal strategic
console, not a user library, not a nutrition workflow and not the legacy operational
Django admin.

## Decision

Admin Analytics now owns its own template shell:

```text
admin_analytics/templates/admin_analytics/base.html
```

All Admin Analytics pages extend this base instead of `notas/base.html`.

The console keeps the existing staff-only URLs:

```text
/staff/analytics/
/staff/analytics/accounts/
/staff/analytics/ai-assistant/
/staff/analytics/product-activity/
/staff/analytics/food-catalog/
/staff/analytics/nutrition-solver/
/staff/analytics/alerts/
```

The URL remains staff-oriented, but the visual system is now independent.

## Consequences

```text
- Admin Analytics no longer inherits the normal My Scoope sidebar/header.
- The dashboard has its own sidebar, topbar and CSS scope.
- The existing Django admin remains available as legacy/operational admin.
- Admin Analytics remains read-first and does not execute domain business logic.
```

The legacy admin distinction is deliberate:

```text
Django admin / previous operational surfaces = object-level/manual operations.
Admin Analytics = strategic product intelligence and health monitoring.
```

## Migration impact

No database migration is required. This patch only changes templates, CSS and docs.
