# GFC00-GFC10 · Generic Food Coverage

Status: active
Date: 2026-07-17
Target branch: `feature/generic-food-coverage`
Baseline: `09cb4f9` on top of local `staging`

## Purpose

Build a measurable, evidence-backed catalog of generic foods relevant to Chile,
starting with vegetables, fruits, meats and seafood, legumes, and unbranded dairy.
The cycle turns catalog growth from an open-ended import exercise into a coverage
program without making the coverage plan a whitelist.

The final target count was not fixed in advance. The initial working range of
350-600 food concepts was a planning hypothesis only. Enumeration, preparation
review, and duplicate normalization produced a version 1 baseline of **282 targets**:
87 vegetables, 53 fruits, 77 meats and seafood, 36 legumes, and 29 unbranded dairy
foods. This is the measurable baseline, not a ceiling or whitelist.

## Product outcome

At closure, Admin Operations can answer all of these questions quantitatively:

- Which generic foods do we intend to cover?
- Which targets have a trustworthy source mapping?
- Which targets were dry-run, imported, reviewed, published, and snapshotted?
- Which categories or Chile-relevant foods are still missing?
- Which useful foods were discovered outside the original plan?
- Why was any target deferred, replaced, or excluded?

## Non-negotiable boundaries

1. The coverage manifest is a planning and measurement artifact, not a whitelist.
2. A useful discovered food may enter the catalog when it passes the same evidence,
   quality, licensing, and review rules as a planned target.
3. Manifest rows are never materialized as `CatalogFood` until real source data is
   available and the governed dry-run/apply flow succeeds.
4. No source in this cycle writes directly to `notas.Food`.
5. Importing does not publish.
6. Publishing does not create or refresh an operational snapshot.
7. Picker, Meals, Solver, and MCP continue to consume `notas.Food`.
8. Every data mutation requires an equivalent, current dry-run first.
9. USDA Branded is excluded. Brand work is deferred to a later cycle.
10. Open Food Facts remains reference-only while its persistence license gate is
    closed. FatSecret remains outside the cycle.
11. Synthetic test data never becomes catalog data.
12. One patch equals one commit; no patch is merged with CI failing or a hard
    regression in privacy, evidence, publication, snapshots, or architecture.

## Inclusion contract

A target belongs in the generic coverage manifest when it is:

- generic and not identified by a commercial brand;
- reasonably consumed, purchased, or used for meal planning in Chile;
- nutritionally meaningful as a distinct food or justified preparation state;
- representable with trustworthy per-100-g nutrition data;
- attributable to an allowed source or independent manual evidence;
- useful in Picker, Meals, and Solver after explicit publication and snapshot.

Preparation variants are separate targets only when at least one applies:

- cooking materially changes water content or per-100-g nutrition;
- the variant is selected as a distinct ingredient in real meal planning;
- the edible portion differs materially;
- the source provides a clear and independently traceable food record.

Targets are excluded or deferred when they are:

- branded products;
- restaurant-specific dishes or proprietary recipes;
- duplicate synonyms with no nutritional or preparation distinction;
- unsupported extrapolations or invented nutrition rows;
- too ambiguous to map safely to a source and preparation state;
- outside the first-cycle categories.

## Taxonomy baseline

The first version enumerates these roots and refines them before setting counts:

| Root | Initial subcategory direction |
|---|---|
| Vegetables and greens | leafy, cruciferous, roots, tubers, bulbs, stems, fruit vegetables, mushrooms, sea vegetables |
| Fruits | citrus, berries, pome, stone, tropical, melons, grapes, dried fruit where operationally useful |
| Meat, poultry, and seafood | beef, pork, lamb, goat, poultry, game where relevant, fish, shellfish, organ meats |
| Legumes | beans, lentils, chickpeas, peas, soy, lupin, dry and cooked variants where justified |
| Unbranded dairy | milk, fermented milk, yogurt styles, fresh and aged generic cheese, cream, butter, whey-derived generic foods |

The taxonomy must preserve `food_group`, `food_subgroup`, and explicit preparation
state so category progress is computable rather than inferred from display names.

## Manifest contract

The versioned manifest is source-controlled data separate from the catalog. Each row
has at least:

```text
target_key
preferred_name_es
category
subcategory
preparation_state
priority_tier
chile_relevance
expected_source
source_food_id
source_dataset
source_version
mapping_status
catalog_food_id
coverage_status
discovery_origin
decision_reason
```

Stable `target_key` values survive source remapping and display-name refinement.
Source IDs and catalog IDs are nullable until those stages actually occur.

## Coverage funnel

Progress is reported as separate stages, never as one inflated total:

```text
defined
  -> source_mapped
  -> dry_run_valid
  -> imported
  -> reviewed
  -> published
  -> snapshotted
```

Required metrics:

- count and percentage by category, subcategory, priority tier, and stage;
- unmapped and blocked targets with reasons;
- discovered foods inside and outside the frozen manifest;
- duplicate and replacement decisions;
- source distribution and source-version distribution;
- nutrition completeness, portion completeness, and Spanish naming completeness;
- published-without-snapshot and snapshot-drift counts.

## Source strategy

Priority order:

1. USDA Foundation Foods for commodity and minimally processed foods.
2. USDA SR Legacy to fill generic coverage gaps not represented in Foundation.
3. Independent manual evidence for Chile-relevant gaps or source ambiguity.

FNDDS may be considered only for a later explicit decision because survey foods can
represent consumed dishes and composite preparations rather than the generic
ingredient boundary of this cycle.

USDA rows must retain FDC ID, data type, release/version, attribution, source URL or
dataset reference, input hash, and import batch.

## Priority tiers and waves

The list is enumerated before counts are frozen, then ranked:

- Tier A: essential foods expected in everyday meal planning;
- Tier B: broad common coverage;
- Tier C: useful depth, less common varieties, and justified preparations;
- Discovery: useful foods found after the manifest version was frozen.

Operational waves are limited independently from tier size:

- Wave 0: 5-10 foods to validate the mapping and import contract;
- Wave 1: up to 25 foods after a clean Wave 0 and idempotent replay;
- Wave 2: up to 50 foods after category and quality review;
- later waves: maximum governed by source policy and two consecutive clean runs.

## Quantitative closure criteria

- 100% of manifest rows have a stable target key and category/subcategory.
- 100% of imported rows have `CatalogFoodSource` and a non-null apply batch.
- 100% of apply batches correlate to an equivalent dry-run.
- 100% of USDA mappings retain FDC ID, data type, release, and attribution.
- 100% of imported foods have protein, carbohydrate, fat, calories or an explained
  derivation, and explicit preparation state.
- 100% have a Spanish preferred name before review completion.
- At least 90% of reviewed foods have a useful default portion.
- Fewer than 3% unresolved probable duplicates at each wave gate.
- 0 branded foods imported through this cycle.
- 0 automatic publications and 0 automatic snapshots.
- 0 private operational foods promoted automatically.
- Every discovery is either added to the next manifest version or explicitly
  classified as catalog-only with a reason.

## Patch plan

### GFC00 · Cycle contract and audited baseline

- Add this plan and active-cycle index entry.
- Record the non-whitelist rule and derived-count approach.
- Confirm local branch, catalog counts, migration state, and test baseline.

### GFC01 · CI baseline closure

- Diagnose the legacy view tests redirected by the onboarding gate.
- Preserve production onboarding behavior while making test setup explicit.
- Run focused regressions and the full Django suite.

### GFC02 · Coverage manifest contracts

- Add typed parsing, validation, stable keys, stage values, and duplicate checks.
- Keep manifest rows outside Django persistence and outside `CatalogFood`.
- Add fixtures only for parser tests, never as real catalog data.

### GFC03 · Taxonomy and version 1 enumeration

- Enumerate roots and subcategories using inclusion rules.
- Build the real target list in Spanish with preparation states and tiers.
- Derive the final target count after normalization and duplicate review.
- Result: 282 targets (84 tier A, 172 tier B, 26 tier C); 20 are already
  source-mapped to the governed internal seed and 262 await external mapping.

### GFC04 · USDA source mapping

- Reuse the existing USDA reader/mapper/importer.
- Add Foundation and SR Legacy mapping support for manifest targets.
- First SR Legacy gate: 10 explicitly mapped FDC IDs across all five roots;
  read-only validation against the official 2018-04 dataset produced 10 valid,
  0 invalid, 0 duplicate, and 10 importable candidates.
- Produce mapping confidence, ambiguity, duplicate, and unmapped reports.

### GFC05 · Coverage observability in Admin Operations

- Add category funnel, target status, source mapping, blockers, and discovery views.
- Keep selectors read-only and mutations in auditable services.
- Do not expose raw secrets or oversized source payloads.

### GFC06 · Essential Wave 0 and Wave 1

- Execute local dry-run/apply for 5-10, then up to 25 real generic foods.
- Review every row and replay idempotently before increasing volume.
- Do not publish automatically.

### GFC07 · Tier A completion

- Complete source mapping and imports for the enumerated essential tier.
- Resolve Spanish aliases, portions, preparation states, and category gaps.

### GFC08 · Tier B and category breadth

- Expand by category using governed batches and quality gates.
- Hold ambiguous mappings for manual evidence instead of guessing.

### GFC09 · Discovery and manual gap closure

- Formalize useful out-of-manifest discovery intake.
- Add Chile-relevant gaps with independent evidence and manifest versioning.
- Demonstrate that discovery can expand the target count without bypassing review.

### GFC10 · Closure and operational handoff

- Reconcile manifest, catalog, publications, and snapshots.
- Run full CI and architecture/privacy/publication regressions.
- Publish metrics, unresolved gaps, next manifest version rules, and staging runbook.

## Go/no-go rules

Stop a wave when any occurs:

- the input hash or parameters differ from the approved dry-run;
- an unexplained import error or orphan source/batch appears;
- probable duplicates exceed 3%;
- a branded or insufficiently evidenced food crosses the boundary;
- a source mapping is ambiguous between materially different foods or preparations;
- import causes publication or snapshot side effects;
- focused or full CI exposes a hard regression.
