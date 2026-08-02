# Decision 0161: architectural and quality debt is controlled by ratchets

Date: 2026-08-02
Status: accepted
Cycle: TDG03

## Context

The repository had no executable statement of allowed application dependencies, a
production import cycle between AI credit and usage modules, and no automated check
for known vulnerable dependencies or fatal static-analysis errors. Applying a broad
style formatter as a gate would mix historical cosmetics with correctness work and
produce a migration too large to review safely.

Admin Operations application services also emitted Django messages directly. That
made an application result depend on an HTTP request and encouraged interface
concerns to spread into a strategically important domain.

## Decision

- Record the current cross-application import graph as executable policy in
  `core.application_dependencies`.
- Name bidirectional transitional edges and require any new edge to be reviewed in
  the policy change that introduces it.
- Reject every production Python module cycle.
- Move model pricing to a dependency-neutral module so credit conversion and usage
  observation no longer import each other.
- Keep Admin Operations message rendering in its interface layer and ratchet the
  remaining HTTP object-lookup debt so it cannot grow.
- Gate Ruff's fatal correctness families (`E9`, `F63`, `F7`, `F82`) now. Broader
  historical style cleanup remains incremental instead of blocking feature work.
- Audit the deployed dependency lock for published vulnerabilities in CI.

## Consequences

- Architectural coupling becomes a visible decision rather than an incidental
  import.
- Removing transitional edges is encouraged; adding one requires explicit evidence.
- Known vulnerable direct and transitive packages fail the quality job.
- The initial dependency remediation upgrades Django, cryptography, idna, PyJWT,
  requests and urllib3 to patched compatible releases without changing product
  behavior.
- Style improvement can continue in reviewable slices while undefined names and
  syntax/import failures are blocked immediately.
