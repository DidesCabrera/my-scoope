# Decision 0150: keep Open Food Facts reference-only pending ODbL approval

## Status

Accepted for FCG08 on 2026-07-17.

## Context

Open Food Facts is already integrated as an external lookup provider, temporary reference and curation-candidate source. FCG08 evaluated whether API results could also be persisted as `CatalogFood` alongside internal, USDA, authorized-brand and manually curated records.

The official API documentation states that the database is licensed under the Open Database License (ODbL), individual contents under the Database Contents License, and product images under CC BY-SA. Open Food Facts also describes attribution and share-alike obligations. Its official reuse guidance warns that combining OFF data with another database can require the resulting database to be released as open data under compatible terms.

Sources reviewed on 2026-07-17:

- https://openfoodfacts.github.io/openfoodfacts-server/api/
- https://blog.openfoodfacts.org/en/news/how-digital-responsibility-goals-helped-us-develop-a-better-technology

## Decision

Open Food Facts remains `lookup/reference-only` in My Scoope. FCG08 does not persist OFF nutrition records as `CatalogFood`, and it does not copy OFF product images.

The governed import boundary rejects any mutating batch whose source type is `open_food_facts`. Existing lookup, attribution, external-reference hashes and curation-candidate workflows remain available.

Persisting OFF data may be reconsidered only after an explicit product/legal decision defines:

- whether the combined Food Catalog database will be publicly redistributed;
- the license applied to that database;
- attribution placement;
- which fields are database contents versus independently sourced facts;
- image exclusion or compliant image handling;
- compatibility with every other combined source.

## Consequences

- OFF-created `CatalogFood` count remains zero.
- OFF can inform demand and manual/authorized curation, but a curator must provide independent evidence under an approved license before creating a master record.
- FatSecret remains outside FCG00-FCG10 and is unaffected.
- The guard is a hard regression boundary and must remain covered by tests.
