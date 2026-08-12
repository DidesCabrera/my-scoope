# 0150 - Governed, multidimensional Food Catalog enrichment

Status: accepted
Date: 2026-08-12
Cycle: CE01–CE10

## Decision

Codex may enrich internal `CatalogFood` values against the connected production database only through bounded manifests, equivalent dry-runs, an allowlisted transactional apply service, optimistic concurrency checks, and an append-only before/after ledger. Enrichment does not approve, publish, or snapshot a food.

Capability classification is multidimensional. Nature, provenance, consumers, maturity, per-food assessment, authority, risk, and scope are independent properties. A solver requirement therefore does not imply a particular evidence source, maturity, or approval policy.

Stable and critical values remain typed fields. Evolvable client capabilities use versioned definitions and per-food assessed values until their usage justifies promotion. Clients declare requirements; Food Catalog owns values and their governance.
