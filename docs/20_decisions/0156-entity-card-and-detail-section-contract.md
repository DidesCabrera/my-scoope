# 0156 - Entity Card and Detail Section Contract

Status: accepted
Date: 2026-07-19

## Context

Food, Meal, DailyPlan and Program cards shared the same anatomy but expressed it only through generic legacy classes. Detail section headings were shared indirectly through names tied to DailyPlan and Home.

## Decision

Declare neutral contracts:

```text
entity-card
entity-card__main
entity-card__title
entity-card__kpi
entity-card__footer
entity-card__metadata
entity-card__actions

detail-section-header
detail-section-heading
```

Entity templates remain separate compositions. The shared classes own anatomy and appearance; entity/feature classes own content and bounded layout variants.

## Consequences

- Programs participates in the same card and detail-section system.
- Shared CSS ownership becomes explicit.
- Existing selectors and JavaScript remain compatible.
- A future migration can remove legacy aliases after broader visual regression coverage.
