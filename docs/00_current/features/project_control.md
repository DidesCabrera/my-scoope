# Project Control, Clarity & Foresight

Status: current
Last updated: 2026-07-18

## Purpose

My Scoope exposes one sanitized evidence layer for Felipe, staff, developers, and AI
clients. It connects environment readiness, release identity, migrations, safe data
aggregates, architectural transitions, current documentation, and product bets without
becoming a generic command runner or a second source of domain truth.

## Surfaces

```text
python manage.py diagnose_environment
  -> environment and integration readiness; no network calls or secret values

python manage.py project_status
  -> release, runtime, migrations, capabilities and safe aggregate probes

Admin Operations > Project Control
  -> staff-only, GET-only view of the same project-status contract

python manage.py document_registry
  -> cycles and decisions with status, domain and identifier validation

python manage.py project_portfolio
  -> hypotheses, evidence, next experiments and decision signals

python manage.py ai_project_context
  -> compact composition of the contracts above for an AI client
```

All commands support structured JSON where useful. `ai_project_context` accepts a
domain filter so an AI can request relevant decisions without loading the entire
decision history.

## Authority

- Domain apps own their data and business operations.
- `core.project_status` aggregates safe evidence; it does not reimplement domain rules.
- Admin Operations renders status and attention items but has no Project Control POST
  action.
- The document, transition, and portfolio registries are versioned current sources.
- A probe failure is isolated and visible; it never authorizes an automatic mutation.

## Security and privacy

- Configuration exposes presence and classification, never values.
- Project status contains aggregates, not catalog rows or user identities.
- OAuth diagnostics check Site/SocialApp shape without revealing client credentials.
- AI context has regression coverage against secrets, passwords, and private emails.
- Project Control remains protected by Django staff access and rejects POST.

## Operational interpretation

An `ok`, `warning`, or `error` finding is evidence for judgment, not a prescribed
decision. Warnings include uncertainty that the system cannot resolve alone, such as
OAuth clock validity without an external trusted time source. Staging operators should
compare new probes against known reality before treating them as authoritative.

## Staging handoff

1. Deploy the PCF branch commit and configure release identity.
2. Confirm Project Control reports the deployed commit and zero pending migrations.
3. Compare OAuth, email, Sentry, AI, solver, Food Catalog, and operational-food signals
   against the known staging configuration.
4. Confirm the route is staff-only and POST returns 405.
5. Confirm a push to `staging` executes the full GitHub Actions gate.
6. Record ambiguous or inaccurate probes as product evidence and correct them before
   relying on the surface for release decisions.

