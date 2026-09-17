# Decision 0199: Central Food Catalog authority and versioned delivery

Status: accepted
Date: 2026-09-17

## Context

Food Catalog data currently lives inside each My Scoope environment. That makes
source acquisition, normalization and human curation repeatable work: a food
approved in one environment is not automatically available in another. Directly
connecting staging and production to a shared database would remove duplication,
but it would also couple user requests, migrations and failures across systems.

## Decision

My Scoope will run one central Food Catalog authority with its own PostgreSQL
database. The authority acquires, curates, versions and publishes foods. Consumer
environments receive approved immutable releases over a protected HTTP export and
import them transactionally into local `CatalogFood` mirrors.

Delivery is asynchronous and pull-based:

```text
external sources / human curation
              ↓
central CatalogFood authority
              ↓ publish + build + approve
immutable release (schema + version + SHA-256)
              ↓ explicit import
staging local catalog mirror
              ↓ explicit materialization
staging notas.Food
              ↓ same approved release after validation
production local catalog mirror -> production notas.Food
```

The central service is not a runtime dependency of meals, plans, programs,
Solver, MCP or AI. Those capabilities continue to read only local `notas.Food`.

Only `published` foods enter releases. Publication is an all-or-nothing guarded
batch and release approval is a separate recorded decision. Import checks schema,
food count and SHA-256, rejects reuse of a version with another checksum, and
deprecates absent previously-managed mirrors rather than deleting them.

The first Render topology is one web service plus one PostgreSQL database. A
worker is intentionally omitted until measured volume requires scheduled or
asynchronous jobs. The central service initially uses the same repository to
reuse the domain code, but runs a reduced Django settings module and independent
database. Repository separation may happen later without changing the release contract.

## Consequences

- Food acquisition and curation happen once.
- Staging and production can validate and promote the exact same payload.
- A central outage does not interrupt product reads or existing user workflows.
- Consumer databases retain a local mirror for traceability and a separate
  operational snapshot for domain stability.
- Releases require explicit operational promotion; new central data is not
  instantly visible to users.
- Initial migration needs a temporary protected snapshot export from staging,
  disabled immediately after cutover.
- Secrets are scoped to the authority web service and consumer web services;
  workers do not receive them unless they later perform imports.
