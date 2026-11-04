# Catalog curation framework

Adapt these dimensions to the catalog and intended use: identity, provenance, completeness, validity, consistency, uniqueness, fitness, freshness, traceability, and operability.

## Foods

Check preparation state, generic versus brand identity, solid/liquid basis, reference quantity, serving limits and steps, taxonomy, nutrient completeness, source confidence, solver eligibility, and snapshot behavior. Never conflate raw/cooked, dry/hydrated, salted/unsalted, drained/undrained, or generic/branded variants without an accepted rule.

## Meals

Check occasion and intended use, constituent Foods, servings, reproducible nutrition totals, structure, dietary attributes, visibility, and whether variants add real value.

## Daily Plans

Check target segment and purpose, meal distribution, daily nutrition totals, constraints, diversity, repeat rules, dependence on published Meals, and whether the plan is reusable without private assumptions.

## Review states

- `raw`: preserved source data.
- `normalized`: transformed to the working schema.
- `needs_review`: ambiguity or failed rule remains.
- `approved`: evidence and criteria accepted by the responsible reviewer.
- `published`: written to the authorized destination.
- `retired`: no longer offered, with its reason recorded.

Approval and publication are distinct events.

## Source strategy for national coverage

Evaluate each candidate source on:

- relevance to foods actually consumed in the target country;
- authority and scientific or institutional basis;
- nutrient and portion completeness;
- distinction between generic foods, preparations, and branded products;
- methodology, date, update frequency, and geographic representativeness;
- stable identifiers and ability to reconcile records across sources;
- license, permitted reuse, attribution, redistribution, and commercial-use terms;
- acquisition and maintenance cost;
- expected coverage of priority searches and user-created substitutes.

Use an explicit source tier rather than calling every record “verified”:

1. official or nationally authoritative evidence;
2. recognized scientific or institutional evidence;
3. manufacturer or product-label evidence for branded products;
4. complementary commercial or international data mapped to the national context;
5. community or internal candidate awaiting stronger review.

The tier does not automatically determine publication. Define allowed uses,
minimum required fields, conflict resolution, and reviewer authority for each
catalog and batch. Preserve provenance at field level when one record combines
values from multiple sources.
