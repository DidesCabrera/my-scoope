# Decision 0151: govern Food Catalog growth and keep publication handoff explicit

## Status

Accepted in FCG10; operational staging samples remain pending.

## Decision

Every persistent Food Catalog source must execute through a recorded dry-run and an equivalent mutating `CatalogImportBatch`. Every created or updated master record must retain a `CatalogFoodSource` linked to that mutating batch.

The equivalence guard covers source type/name/version, input SHA-256, normalized parameters and row count. A dry-run expires after 24 hours. Scaling beyond the source sample limit requires an enabled `CatalogImportSourcePolicy`, an explicit maximum, an inactive kill switch and two successful governed sample applies.

Import, publication and operational materialization are three separate actions:

```text
source -> governed CatalogFood candidate
curation -> published CatalogFood
explicit snapshot -> notas.Food
```

Admin Operations records each mutating action with actor and reason. Publishing never creates `notas.Food`; snapshot creation rejects unpublished catalog records and duplicate initial snapshots.

Picker, Meals, Solver and MCP continue consuming `notas.Food` and operational IDs. They do not read `CatalogFood` or provider identifiers directly.

## Source decisions

- internal seed: exactly 30 packaged real seed rows, imported but not published;
- USDA: own source type and governed sample of up to 10 before scaling;
- brands: authorization, label evidence and authorization reference required;
- manual: explicit evidence, license, attribution and version required;
- operational backfill: only global, verified and active `notas.Food`; private foods are excluded by query and regression test;
- Open Food Facts: reference-only pending separate ODbL decision 0150;
- FatSecret: outside FCG00-FCG10.

## Consequences

- Historical batches may remain uncorrelated, but every new FCG apply must reference its dry-run.
- Real staging data is loaded only through the documented runbook after deployment.
- A hard failure in privacy, license, dry-run equivalence, publication/snapshot separation or consumer boundary blocks merge and scale.
