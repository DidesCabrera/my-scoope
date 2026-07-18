# Decision 0152: executable Project Control and AI context

Status: accepted
Date: 2026-07-18

## Context

My Scoope had strong app boundaries, extensive decision history, operational staff
workflows, and disciplined cycle documents. Its current state still had to be rebuilt
manually across settings, Git branches, migrations, commands, dashboards, and long
documents. The same ambiguity affected Felipe, developers, and AI clients.

Adding more procedural rules would not solve that problem. The project needed reliable
context and feedback while preserving judgment about the best path.

## Decision

My Scoope adopts an executable, sanitized project-control layer:

- environment variables have a classified, secret-free contract;
- environment diagnostics report actionable readiness without network calls;
- one project-status service owns safe release, runtime, migration, capability, and
  aggregate probes;
- Admin Operations renders that contract through a staff-only, GET-only control plane;
- cycles and decisions have an executable metadata registry;
- compatibility bridges have purpose, consumers, and exit evidence;
- product direction is expressed as evidence-led bets with continuation and
  reformulation signals;
- AI clients receive a compact composition of these existing contracts rather than a
  parallel hand-maintained prompt or context dump.

The layer is firm about consequences and visibility but flexible about method. A signal
informs a decision; it does not automatically prescribe one.

## Consequences

- `staging` push CI now matches the documented integration policy.
- WSGI and ASGI use the same explicit production settings default.
- Invalid numeric environment configuration fails with the variable name.
- New root-level generated reports and local database backups are kept out of source
  control while explicitly allowlisted historical reports remain preserved.
- Project Control must remain read-only unless a later decision introduces a specific,
  audited domain operation; a generic command executor is forbidden.
- Domain models and services remain the source of business truth.
- Staging must validate release identity and probe accuracy before the control plane is
  treated as release authority.

