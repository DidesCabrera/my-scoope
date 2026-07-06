# 0059 · Admin Analytics Food Catalog quality metrics

Status: accepted
Date: 2026-07-04

## Context

After ADM05, Admin Analytics can observe product activity from `notas`. The next
strategic need is to see whether the independent `food_catalog` app is becoming a
reliable master catalog for future solver quality and operational snapshots.

Food Catalog already owns master records, evidence, portions, aliases, external
provider references, curation candidates and import batches. These signals should
be visible to staff without entering Django Admin table by table.

## Decision

Add a dedicated staff-only read-first page:

```text
/staff/analytics/food-catalog/
```

The page is implemented inside `admin_analytics` and reads existing Food Catalog
tables through selectors/services:

```text
CatalogFood
CatalogFoodPortion
CatalogFoodAlias
CatalogFoodSource
CatalogImportBatch
ExternalFoodReference
ExternalProviderFetchLog
CatalogCurationCandidate
```

ADM06 does not create models, migrations or analytical snapshots. It preserves
the rule that Food Catalog owns catalog data and Admin Analytics consumes it for
strategic visibility.

## Consequences

Staff can now inspect:

```text
catalog volume by status/source
published and verified coverage
solver_enabled coverage
average data_quality_score
low-quality and needs-more-evidence counts
portion/alias/source completeness
license status of evidence
import batch results by status/source
external provider references and fetch health
curation candidate queue by status/reason
```

The dashboard still does not execute curation, publish foods, import data or
write operational `notas.Food` snapshots. Those actions remain owned by Food
Catalog and later domain workflows.

## Follow-ups

Future patches can improve this module with duplicate detection, search quality
signals, source freshness thresholds, and explicit Food Catalog to Solver
readiness scoring once the solver quality dashboard is added.
