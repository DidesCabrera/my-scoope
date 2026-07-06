# 0065 · Admin Analytics compact filter bar

Status: accepted
Date: 2026-07-04

## Context

After ADM10.1, Admin Analytics became an independent staff-only console. The experience
improved, but the shared filters were still rendered as a large `card-detail-block` at
the top of every analytics page.

That made the dashboard feel heavier than necessary because period and segment controls
are global console controls, not the primary content of each analytics module.

## Decision

Move the shared Admin Analytics filters into a compact sub-header below the console
topbar.

The filter UI now lives in the independent shell and is rendered once per page as a
horizontal `admin-analytics-filterbar`.

Each content template stops rendering the old large filter card directly.

## Consequences

- The dashboard content starts closer to the top of the viewport.
- Filters remain available on every Admin Analytics page.
- Query parameters are unchanged: `period` and `user_segment`.
- The filter surface is visually part of the console chrome, not a repeated content card.
- No models or migrations are added.
