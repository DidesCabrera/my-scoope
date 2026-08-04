# Production & Architecture Remediation Cycle

Status: active
Date: 2026-08-03
Cycle code: PAR

## Objective

Close the reviewed production and architecture findings without combining a
launch-safety change, a data migration and a frontend rewrite in one release.
The sequence is risk-first: prevent data loss, make production reproducible,
exercise PostgreSQL, then converge ownership and reduce structural debt.

## Invariants

- `accounts` is the only authority for commercial plans, entitlements,
  subscriptions and credit balances.
- `billing.ProviderSubscription` is provider evidence projected into
  `accounts.AccountSubscription`; consumers never use it as entitlement state.
- `ai_assistant.AIUsageEvent` owns provider/tokens/cost observability, not the
  commercial balance.
- `notas.Profile` is the nutrition/user profile. Legacy `notas.Plan` data is not
  a commercial authority, and `notas.Subscription` means the nutritionist/member
  relationship until it receives an unambiguous name.
- Production can only boot with an explicit PostgreSQL URL.
- `core` and `nutrition_solver` remain service-only apps without schema models.

## Patch sequence

| Patch | Status | Findings | Exit evidence |
| --- | --- | --- | --- |
| PAR00 · Executable baseline | completed | all | Findings mapped to ordered patches, tests and rollback boundaries. |
| PAR01 · Fail-closed production database | completed | P1 | Missing/non-PostgreSQL `DATABASE_URL` raises `ImproperlyConfigured`; subprocess regression tests pass. |
| PAR02 · Render Blueprint | completed | P2 | `render.yaml` versions web, notification worker, housekeeping cron, Postgres and Key Value; migrations run pre-deploy. |
| PAR03 · PostgreSQL CI | completed | P4 | A dedicated GitHub Actions job runs migrations and the complete Django suite against PostgreSQL 17. |
| PAR04 · Recovery operations | completed repository-side | P5 | Backup/restore runbook defines RPO/RTO, PITR, logical export and a recurring restore drill. First real drill remains an external launch gate. |
| PAR05 · Launch defaults | completed | P6, P7, P8 | One-year HSTS defaults, subdomains/preload enabled, 5% production traces, `es-cl` and `America/Santiago`; regression test locks the contract. |
| PAR06 · Commercial authority convergence | completed repository-side | A1 | Runtime, Admin Operations, analytics, reports and validation use account-owned credit projections; legacy models are read-only and guarded from production consumers; reconciliation distinguishes official integrity from optional pre-cutover parity; hard blocks migrate to `CreditWallet`; `NutritionistMemberRelationship` is the unambiguous proxy over the historical table. Physical legacy-table removal remains a later compatibility release. |
| PAR07 · Asynchronous AI turn runtime | completed repository-side | P3 | PostgreSQL-owned job model with idempotency, conversation lanes, leases, retries and retention; Redis wake-up channel; dedicated Render worker; private `202` submit/poll flow with mobile network retry; synchronous rollback flag. Calendar notifications already use durable event/delivery records under their continuous worker. |
| PAR08 · Structural decomposition | active | A2, A3 | A2 complete: `notas.domain.models` is a 91-line compatibility façade and every concrete model is physically owned, with zero migration drift. A3 started: orchestration helpers left the main orchestrator behind its existing characterization suite; the other reported hotspots remain incremental work. |
| PAR09 · Quality and frontend toolchain | active | A4, A5 | Ruff gained a comprehension ratchet and scoped strict mypy. A pinned Node/esbuild pipeline, native JS tests and CI/Render build now exist; the tested async polling client is the first bundled module. CSS hotspot decomposition remains visual-regression work. |
| PAR10 · Repository hygiene | partially completed | A6, A7 | Service-only invariant is executable. Five merged local branches were removed; the unmerged calendarization branch, `main`, `staging`, a checked-out worktree branch and all remote refs were preserved for owner review. |

## Release order

```text
Release 1: PAR01-PAR05
  -> no schema changes; deploy/operations hardening

Release 2: PAR06
  -> data reconciliation and authority cutover; own rollback plan

Release 3: PAR07
  -> new asynchronous API/worker behavior behind a feature flag

Ongoing: PAR08-PAR10
  -> small independently reversible debt-reduction patches
```

## External launch gates

- Validate and apply the Blueprint in Render without creating duplicate services.
- Populate every `sync: false` secret and enable Web Push only after VAPID smoke tests.
- Run `python manage.py check --deploy` in the pre-deploy environment.
- Confirm the paid PostgreSQL plan has recovery enabled.
- Complete and record one restore drill before public launch.
- Observe p95/p99 web and AI latency after enabling the 5% trace sample.

## Deferred-by-design risks

PAR07 is implemented behind a production-default feature flag and should be
promoted only after worker/API staging smoke evidence. PAR06 has repository-side executable evidence, but its data
reconciliation command must still be run against a production snapshot before
the release is promoted. Physical removal of legacy tables is intentionally a
later compatibility release.
