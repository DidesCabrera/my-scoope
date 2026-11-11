# Catalog–solver contract

Use this reference when the solver needs new catalog variables, different
semantics, stronger validation, or a change to eligibility. The contract is a
negotiated interface: the solver states what decision it must make and why;
Catalog Operations states what information can be supplied reliably and how it is
governed.

## Contract record

For each variable or relationship, define:

| Field | Required meaning |
|---|---|
| Consumer decision | What solver decision depends on this value |
| Entity and field | Food, portion, Meal, Daily Plan, relationship, or derived value |
| Semantic definition | Exact meaning, population, preparation state, and exclusions |
| Type and unit | Data type, canonical unit, precision, and conversion rule |
| Cardinality | Required, optional, repeated, mutually exclusive, or conditional |
| Valid range | Bounds, accepted values, and impossible combinations |
| Missing state | Difference between unknown, unavailable, not applicable, and zero |
| Provenance | Source or derivation required and confidence or review state |
| Eligibility effect | Whether absence or low confidence excludes, penalizes, or labels a candidate |
| Version behavior | Contract version, compatibility, refresh, and snapshot expectations |
| Validation | Deterministic checks and review evidence |
| Owner | Producer, consumer, reviewer, and escalation path |

Do not request a field merely because it could be useful. Tie it to an observed
failure, a product requirement, or a measurable solver decision. Prefer the
smallest contract that supports the intended behavior without making uncertain
catalog information look authoritative.

## Handoff sequence

1. The Solver Steward supplies the failing scenario, decision need, current
   workaround, proposed semantics, and acceptance test.
2. The Catalog Curation Steward evaluates source availability, reliability,
   curation cost, coverage, licensing, publication impact, and refresh behavior.
3. Both roles identify whether the requirement belongs in source data, normalized
   catalog data, an operational snapshot, a derived solver feature, or product
   policy. Do not place every derived value into the catalog.
4. Architecture reviews authority, versioning, migration, and downstream effects
   when the boundary changes materially.
5. Felipe resolves material product, investment, or domain tradeoffs. A qualified
   reviewer resolves new nutritional or safety rules.
6. Backend implements the accepted version and its validators. The Solver Steward
   verifies the affected evaluation scenarios; Catalog Operations verifies the
   producer-side contract and publication evidence.

## Contract quality checks

- The same term has one meaning across catalog, snapshot, API, and solver input.
- Units and preparation states cannot be confused silently.
- Zero is never used as a substitute for unknown.
- Eligibility and confidence are explicit rather than inferred from field presence.
- Derived values record their inputs and formula or rule version.
- A contract change states compatibility, migration, recomputation, and rollback.
- Catalog publication success does not by itself prove solver usefulness; solver
  evaluation success does not by itself authorize catalog publication.

Return unresolved items as a decision list with owner and evidence needed. Do not
finalize a contract by silently choosing semantics on behalf of the other role.
