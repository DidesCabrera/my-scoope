# Catalog Operations

Status: pilot
Owner: `catalog-curation-steward`
Sponsor and final authority: Felipe Dides
Current project: `PRJ-PROD-003 — Curación de Catálogos`

## Mission

Maintain Foods, Meals, and Daily Plans as trustworthy company assets. Catalog
Operations knows where the information comes from, which data contract it must
satisfy, its current quality and publication state, and how a reviewed change
moves safely into the product.

## Operating structure

### 1. Source intelligence

Maintain the source registry and answer:

- what sources exist and who owns them;
- which catalog and fields each source covers;
- authority, methodology, geography, date, license, cost, and update cadence;
- how the source is acquired and preserved;
- current availability and last verification;
- known gaps, conflicts, and permitted uses.

Primary output: **source landscape and source registry**.

### 2. Data contracts and taxonomy

Maintain the contracts that curated information must satisfy:

- required fields, identifiers, units, taxonomies, relationships, and states;
- field meanings and allowed values;
- validation and publication requirements;
- source-to-working and working-to-product mappings;
- version compatibility and downstream impact.

Primary output: **contract registry, mappings, and exception rules**.

### 3. Curation and publication operations

Operate controlled batches through:

`source snapshot -> raw dataset -> normalization -> review queue -> approved batch -> publication -> operational snapshot`

Preserve raw values, decisions, reviewer evidence, rejected records, and the exact
published batch. Publication remains distinct from approval.

Primary output: **reviewable Sheets/CSV batches and publication evidence**.

### 4. Quality and catalog state

Maintain a dated view of:

- total, reviewed, approved, published, retired, and unresolved records;
- coverage by priority category, user need, and national context;
- completeness, provenance, duplicates, ambiguity, and freshness;
- contract failures and downstream inconsistencies;
- usage, searches without results, substitutions, and user-created gap signals.

Primary output: **catalog health report and prioritized backlog**.

## Catalog responsibilities

| Catalog | Curated authority | Operational consumer | Initial focus |
|---|---|---|---|
| Foods | `food_catalog.CatalogFood` | `notas.Food`, Meals, Daily Plans, Programs, Solver | Chilean coverage, portions, nutrition, source confidence, visual identity |
| Meals | To confirm in baseline | User libraries, Daily Plans, Explore, Programs | Composition, reproducible nutrition, occasions, dietary attributes, publication state |
| Daily Plans | To confirm in baseline | Calendar, Programs, user libraries | Purpose, meal distribution, constraints, totals, diversity, reuse boundary |

## Roles and handoffs

| Participant | Responsibility |
|---|---|
| Catalog Curation Steward | Own source, contract, curation, state, and quality records; prepare batches and recommendations. |
| Strategic Product Advisor | Define priority users, adoption needs, desired coverage, and investment tradeoffs. |
| Nutrition Solver Steward | Define solver-consumption requirements, provide failing scenarios, verify solver usefulness, and return contract exceptions. |
| AI Architecture and Context Steward | Review authority boundaries, snapshots, contracts, and architectural drift. |
| Backend specialists | Implement or correct imports, validations, migrations, APIs, and publication mechanics. |
| Felipe Dides | Approve material scope, policies, external commitments, and consequential publication. |
| Domain reviewer | Resolve nutritional, scientific, licensing, or semantic ambiguity beyond accepted rules. |

## Core registers

1. `source-registry.yaml`: sources, allowed uses, state, evidence, and gaps.
2. `data-contract-registry.yaml`: contracts, owners, versions, validators, and consumers.
3. Working datasets: bounded Sheets/CSV batches with raw and normalized fields.
4. Catalog health report: metrics, contract failures, decisions, and backlog.
5. Publication log: exact batch, reviewer, destination, validation, rollback, and result.

The registries describe operational knowledge; code, migrations, schemas, and the
approved product database remain authoritative for actual behavior and state.

## Initial operating cadence

- Update source or contract state whenever evidence changes.
- Produce a health report at each project milestone and before a material batch.
- Review unresolved exceptions before adding new volume in the affected category.
- Revalidate time-sensitive or licensed sources according to their recorded cadence.
- After publication, reconcile the approved batch with the operational destination.

## Pilot completion evidence

- Current source landscape for nationally relevant Foods.
- Contract registry for the Foods editorial-to-operational path.
- Reconciliation of the existing Sheet, JSON snapshot, CatalogFood, notas.Food,
  and visual identities.
- One curated batch with exceptions, validation, approval, publication, and
  post-publication reconciliation recorded.
- Baseline proposals for Meals and Daily Plans authority and contracts.
