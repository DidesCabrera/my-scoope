# 0069 · Admin Analytics mobile shell and filter drawer

## Status

Accepted

## Date

2026-07-04

## Context

After ADM10.5, the desktop Admin Analytics console had the right independent visual
identity, but the mobile shell still showed the sidebar as a thick header-like block. The
shared filter bar also remained expanded on small screens and consumed too much vertical
space before the analytics content.

## Decision

Admin Analytics uses a mobile-specific console shell:

- The sidebar becomes an off-canvas drawer that opens from the left.
- The mobile topbar exposes a menu icon for navigation and a filter icon for filters.
- The filter bar is collapsed by default on mobile and expands only when the filter icon is
  activated.
- Mobile hides the page subtitle and topbar metadata to preserve vertical space.
- Desktop behavior remains unchanged: sidebar and filters stay visible as console chrome.

## Consequences

- The console no longer feels like a stacked user-app layout on mobile.
- Mobile users can reach navigation and filters without sacrificing the first screen of
  dashboard content.
- The implementation remains CSS/template-only and does not add models or migrations.
