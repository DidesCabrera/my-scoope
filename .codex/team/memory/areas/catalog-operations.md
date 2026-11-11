# Catalog Operations Memory

Status: pilot
Last reviewed: 2026-11-11
Owner role: `catalog-curation-steward`

## Objective

Maintain Foods, Meals, and Daily Plans as trustworthy operational assets through traceable sourcing, normalization, review, publication, and recurring quality control.

## Current initiative

- `PRJ-PROD-003 — Curación de Catálogos` owns the first baseline and operating model.
- Foods has a curated source in `CatalogFood` and an explicit snapshot boundary into `notas.Food`.
- Meals and Daily Plans require baseline evidence, quality criteria, and explicit operational ownership.
- Adoption depends on covering foods used in Chile. No single trustworthy and readily usable national dataset has yet been established, so source discovery, licensing, reconciliation, and progressive validation are strategic work for the area.
- A prior Food Catalog cycle used Google Sheet `13hEtHnxwfsPI0j0BuTfloPqoqaVRRSGVXAjFjNuKOoE` as an editorial source for portion measures. Its approved snapshot is versioned as `food_catalog/data/myscoope_food_portions_v1.json` with 219 foods.
- Commits `499062ff` and `65b8943c` preserve the household-portion contract and food visual-identity implementation respectively. These are the starting baseline for new curation work.

## Role boundary

- Product chooses priority users, use cases, and investment.
- Catalog Operations prepares and maintains the information needed to serve those priorities.
- Architecture protects authority, snapshots, and downstream integrity.
- The Nutrition Solver Steward defines and verifies the contract required by the
  solver, while Catalog Operations owns the records, provenance, curation, and
  publication that satisfy the accepted producer side of that contract.

## Evaluation target

Demonstrate a baseline report, a national-source landscape and gap analysis, a quality rubric, one traceable working dataset, and one bounded curation batch ready for review.

## Chile coverage direction — accepted 2026-10-30

- Felipe confirmed that the immediate problem is catalog coverage, not retroactive
  renaming: users need distinct foods such as marraqueta, hallulla, pan de molde,
  reineta, and other nationally relevant variants instead of only generic `pan`
  or `pescado` records.
- The first expansion should be a forward-looking Chile seed catalog. Historical
  records and plans do not need backfill in this stage. Spain is the likely next
  national expansion, so the method should be reusable by country rather than
  encoded as a Chile-only exception.
- Until My Scoope has meaningful search telemetry, priority must be described as
  expected national consumption and planning utility, not as “most searched in
  My Scoope” or “most searched in Google.” Failed-search evidence may guide later
  batches once it exists.
- Catalog Operations may compile its own nutritional profiles from factual
  nutritional factors supported by multiple or independently assessed sources,
  with My Scoope-owned selection, naming, normalization, portions, and quality
  controls. This complements rather than replaces direct, versioned source
  imports.
- Source licenses, terms, access controls, attribution, and field-level
  provenance remain explicit. The accepted direction does not authorize copying
  a protected compilation, bypassing access controls, or treating uncertain
  reuse rights as approved. Legal review remains an open validation step for
  publication rules, not a reason to delay inventory, source assessment, or
  preparation of reviewable candidates.
- Direct-source records and compiled profiles must remain distinguishable in
  evidence and refresh behavior. A compiled profile may be recalculated when an
  input factor changes; it must not pretend to be a mirror of any one external
  database.

Open design work: define the compiled-profile evidence contract, conflict and
refresh rules, source-risk states, and the first Chile coverage matrix before a
production batch is published.

## Operating structure

The initial area model is documented in `.codex/team/areas/catalog-operations.md`.
Its persistent control registers are:

- `.codex/team/areas/catalog-operations/source-registry.yaml`;
- `.codex/team/areas/catalog-operations/data-contract-registry.yaml`.

The role must know and maintain both the data-source landscape and the contracts
each catalog must satisfy. A prior Sheet may remain useful without being the live
product authority; this distinction must be explicit in every status report.
