# UIS06 — Detail Section Contract Cycle

Status: completed
Date: 2026-07-19
Cycle code: UIS06

## Objective

Normalize repeated section headers in DailyPlan, Program, Program Week and enriched proposal details.

## Delivered

- Added `detail_section.css`.
- Declared `detail-section-header` and `detail-section-heading`.
- Migrated related-meal, food aggregation, week board, week summary, day and food section headers.
- Preserved `dailyplan-detail__children-header` and `home-section-title detail-dp` as compatibility/context classes.
- Moved shared header spacing out of `list.css`.

## Non-goals

- Redesign section hierarchy or typography.
- Replace feature-specific layout classes.
- Normalize Proposal review message sections.

## Acceptance

- Equivalent detail sections share spacing, title alignment and responsive margins.
- Program sections no longer depend exclusively on DailyPlan/Home naming to obtain their base appearance.

## Validation evidence

```text
DailyPlan detail
  -> 2 shared headers and headings rendered

Program detail
  -> shared week-board header rendered

Responsive
  -> desktop margins preserved
  -> 390px mobile margins preserved
```

The smoke used an isolated SQLite copy that was removed after validation. The source database was not modified.
