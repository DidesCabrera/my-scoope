# 0061 · Admin Analytics temporal filters and segmentation

Status: accepted
Date: 2026-07-04
Patch: ADM08

## Context

Admin Analytics already has dedicated read-only pages for executive overview,
accounts, AI Assistant, product activity, Food Catalog and Nutrition Solver.
Those pages were useful as fixed-window dashboards, but product operation needs
controlled ways to compare different time windows and isolate staff activity
from member activity.

## Decision

ADM08 introduces a shared `AdminAnalyticsFilters` object for Admin Analytics.
The filter layer is intentionally small and request-driven:

- period: `7d`, `30d`, `90d`;
- user segment: `all`, `staff`, `members`.

The filters are parsed in `admin_analytics.views`, passed into services and then
into selectors. Views remain staff-only and read-only.

## Rules

- Filters must not mutate domain state.
- Unknown query values must safely fall back to defaults.
- Period filters affect metrics previously described as the current operational
  window.
- User segmentation is applied where the observed model has a direct user owner,
  sender, creator or account user relation.
- Pages that include non-user-owned records may still show global totals when a
  safe user relation is not available.

## Consequences

Admin Analytics can now answer questions like:

- how did activation look in the last 30 or 90 days?;
- is product activity coming from staff testing or member usage?;
- can the same dashboard pages be reused during QA, staging and production
  checks without changing code?

ADM08 does not add models or migrations.
