# CE01–CE10 · Governed Catalog Enrichment

Status: repository implementation complete; staging and production data runs pending
Date: 2026-08-12

## Objective

Allow Codex to enrich internal Food Catalog data directly in the connected staging or production database through bounded, traceable, reversible batches. Enrichment never implies curation approval, publication, or an operational `notas.Food` snapshot.

## Architecture

The existing boundary remains unchanged:

```text
CatalogFood master -> explicit publication -> explicit notas.Food snapshot -> clients
```

The new path is:

```text
read-only audit -> bounded batch -> Codex manifest -> dry-run -> apply -> append-only ledger
```

There is no autonomous worker in this cycle. Codex produces each manifest interactively from the real connected database.

## Multidimensional capability contract

A capability is classified independently by:

- nature: factual, operational, semantic, derived, or commercial context;
- provenance/generation method;
- one or more consumers;
- contract maturity;
- per-food assessment status;
- authority requirement;
- risk;
- contextual scope and validity.

Being requested by the solver does not determine whether a value is factual, experimental, externally sourced, or internally governed.

`CatalogCapabilityDefinition` and `CatalogClientRequirement` let clients declare needs without taking ownership of Food Catalog values. Stable critical fields remain typed columns. Experimental capabilities use `CatalogFoodCapability` until their contract warrants promotion.

## Safety contract

The first contract allowlists only internal fields:

- solver minimum, maximum, step, and enablement;
- food form;
- functional roles;
- meal affinities;
- preparation effort;
- cost band;
- registered evolvable capabilities.

It cannot alter nutrients, sources, lifecycle status, publication state, or snapshots. Apply requires the exact dry-run manifest hash, a fresh dry-run, unchanged food timestamps, a reason, and a transaction. Revert is blocked after subsequent changes and records compensating ledger entries instead of deleting history.

## Operational commands

Run them only with the intended environment configuration and database connection:

```text
python manage.py audit_catalog_enrichment
python manage.py create_catalog_enrichment_batch --ids 1,2,3 --environment staging --reason "..."
python manage.py dry_run_catalog_enrichment manifest.json
python manage.py apply_catalog_enrichment manifest.json --reason "..." --confirm-apply
python manage.py revert_catalog_enrichment_batch <batch-ref> --reason "..." --confirm-revert
```

The audit command is read-only. Batch creation freezes exact IDs and input hashes. The create command emits the context Codex needs, including optimistic concurrency timestamps. Dry-run persists field-level proposals but does not change `CatalogFood`.

## Portion profiles

`catalog-portion-profiles.cl.v1` provides broad orientation ranges for cooked legumes, cereals, proteins, vegetables, tubers, fruit, dairy, oils, condiments, beverages, and mixed dishes. Profiles constrain implausible proposals but do not calculate universal answers. Codex must decide min/max/step for each food and explain any profile selection and adjustment.

## Rollout gates

1. Apply migrations and run the read-only audit in staging.
2. Create a representative 5–10 food staging batch.
3. Produce, dry-run, inspect, apply, and revert that batch.
4. Repeat apply without revert and verify Admin Operations observability.
5. Confirm managed PostgreSQL backup/PITR for production.
6. Run the production audit read-only.
7. Authorize a 5–10 food production batch.
8. Verify exact before/after ledger values and confirm zero publication/snapshot changes.

CE07 and CE08 are operational gates, not repository fixtures. No local database result is evidence of production completion.
