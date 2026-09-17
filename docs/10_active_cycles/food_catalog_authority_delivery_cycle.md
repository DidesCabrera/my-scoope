# FCA00-FCA08 · Food Catalog Authority and Delivery

Status: active · code complete, Render provisioning and data cutover pending
Date: 2026-09-17
Target branch: `feature/food-catalog-authority-releases` -> `staging`

## Outcome

Food Catalog becomes one central data authority. Staging and production do not
query that service while serving users: they import explicit, immutable,
checksummed releases and materialize approved foods into their own `notas.Food`
tables. This removes duplicate acquisition/curation work without coupling product
availability to another service at request time.

## Non-negotiable boundaries

1. External sources enter only the authority.
2. A candidate or verified food is never delivered; only `published` foods enter a release.
3. Publishing, approving a release, importing it and materializing it are separate actions.
4. Staging and production keep their own operational snapshots and never read the authority DB.
5. Meals, plans, programs, Solver, MCP and AI continue to consume `notas.Food` only.
6. A release version is immutable: the same version with a different checksum is rejected.
7. Existing plans do not change because a catalog release changed; only the reusable
   operational food snapshot is refreshed. Historical entities keep their own existing semantics.

## Stages

### FCA00 · Baseline and ownership map — complete

- inspected current Render topology and staging data;
- found 219 `CatalogFood` rows: 30 verified internal foods and 189 USDA pending review;
- found 13 private operational foods and no published catalog foods;
- confirmed that re-acquiring and re-curating per environment is the wrong boundary.

### FCA01 · Release contract — complete

- `CatalogRelease` records candidate/approved/replica state, version, previous version,
  count, payload and SHA-256;
- schema `myscoope.food_catalog.release.v1` carries foods, aliases, portions and sources;
- export accepts only approved releases and a bearer token.

### FCA02 · Authority bootstrap — complete in code

- protected one-time snapshot transfers all current curation states, import batches,
  source links and evidence;
- import requires an empty authority catalog and verifies schema, count and checksum;
- the staging export switch is off by default and must be enabled only for cutover.

### FCA03 · Human publication gate — complete

- verified foods receive a complete-batch preflight;
- simulation is the default;
- `--apply` requires an authority user and uses the protected curation workflow;
- one invalid row blocks the entire batch without partial publication.

### FCA04 · Transactional consumer import — complete

- a release is validated before any mutation;
- import is atomic and idempotent;
- missing previously managed foods become deprecated rather than silently deleted;
- a version/checksum conflict fails closed.

### FCA05 · Operational materialization — complete

- published mirrors create global `notas.Food` snapshots;
- a newer `catalog_version` refreshes the same operational food identity;
- deprecated catalog foods mark their linked operational snapshot stale;
- the command supports validation-only and explicit materialization.

### FCA06 · Render topology — declared, provisioning pending

- one `myscoope-food-catalog` web service;
- one `myscoope-food-catalog-db` PostgreSQL database;
- no permanent worker in the first version;
- staging and production receive only release URL/token configuration;
- the authority runs with `miapp.settings.catalog`, not the full consumer application.

### FCA07 · Initial data cutover — pending

1. deploy the code to staging;
2. create the central service/database and shared delivery token;
3. temporarily enable the staging authority-snapshot export;
4. import all 219 catalog rows into the empty authority;
5. disable the staging export immediately;
6. dry-run and publish the 30 verified foods with an identified actor;
7. build and approve the initial release;
8. validate and import it into staging with `--materialize`;
9. reconcile central, replica and operational counts.

### FCA08 · Production promotion and recurring operation — pending

- production imports the exact release already validated in staging;
- future source imports and curation occur only in the authority;
- a new release is promoted staging-first, then production;
- rollback means re-importing a new corrective release, never mutating an approved payload.

## Verification evidence

- release build/approval/export authentication;
- checksum, count and schema rejection paths;
- authority snapshot round trip and non-empty-target refusal;
- idempotent release import/materialization;
- real update path: v1 creates an operational food, v2 refreshes the same ID;
- deployment topology regression tests;
- targeted Django checks and full repository gate before merge.

## Explicitly deferred

- independent repository/codebase for the authority;
- scheduled release polling;
- queue/worker for large release processing;
- public catalog API;
- automatic production promotion;
- deletion of legacy per-environment curation rows before reconciliation proves it safe.
