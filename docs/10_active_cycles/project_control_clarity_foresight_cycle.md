# PCF00-PCF10 · Project Control, Clarity & Foresight

Status: active
Date: 2026-07-18
Target branch: `feature/project-control-foresight`
Baseline: `a674a8e` on top of the completed local Generic Food Coverage work

## Purpose

Make My Scoope easier to understand, operate, and evolve for Felipe, developers,
and AI clients. The cycle adds connective control around the existing apps; it does
not replace their domain boundaries or impose a fixed implementation script.

The desired outcome is that a project participant can answer, from trustworthy
evidence, what is running, what changed, what needs attention, which decisions are
current, which transitions remain open, and which product bets deserve the next
investment.

## Working premise

Control means making consequences and system state visible. It does not mean
prescribing one universal path. My Scoope should provide context, capabilities,
feedback, and reversible actions so humans and AI can exercise judgment according
to cost, benefit, risk, evidence, and future value.

## Baseline findings

- CI policy names `staging` as the integration branch, but push CI currently runs
  only for `main` and `master`.
- WSGI defaults to production settings while ASGI points to the non-importable
  package name `miapp.settings`.
- Configuration spans dozens of environment values without a public, secret-free
  environment contract or one comprehensive diagnostic.
- `PROJECT_STATE.md` mixes durable product posture with volatile evidence such as
  test counts and cycle completion.
- `docs/10_active_cycles/` contains active, planned, and many completed plans in one
  view; the decision collection is valuable but hard to query by status or domain.
- Admin Operations already provides staff workflows and append-only audit events,
  making it the correct foundation for a read-only project control plane.
- Several orchestration modules have become change hotspots; this cycle will expose
  boundaries and split only where doing so materially improves control or testing.
- Operational JSON reports and local database backups lack an explicit artifact
  location and lifecycle.

## Non-negotiable boundaries

1. Existing domain apps remain authoritative for their own state and operations.
2. The control plane is read-only in this cycle; it must not become a generic remote
   command runner.
3. Diagnostics never expose secret values, credentials, tokens, prompts, or private
   user data.
4. Environment validation may fail closed for invalid production configuration but
   must keep local development understandable and recoverable.
5. Generated evidence must come from code, settings, migrations, or persisted
   aggregate state rather than duplicated hand-maintained claims.
6. Documentation registries improve navigation; they do not discard historical
   rationale.
7. Refactors preserve behavior and are justified by observed responsibility or test
   friction, not a universal line-count limit.
8. No patch mutates application data. Any validation involving data is read-only or
   uses isolated test databases.
9. One patch equals one commit. Focused tests precede each commit and the full suite
   gates closure.
10. No merge is acceptable with failing CI or a hard regression in security,
    privacy, auditability, catalog governance, AI tool boundaries, or solver purity.

## Quantitative outcomes

- Pushes to `staging`, `main`, and `master`, plus all pull requests, trigger CI.
- 100% of declared environment settings are classified without exposing values;
  critical production misconfiguration yields an actionable diagnostic.
- WSGI and ASGI resolve the same explicit production settings default.
- One project-status contract serves CLI JSON, human CLI output, Admin Operations,
  and AI/export consumers.
- The status contract reports release, environment, database/migrations, critical
  capabilities, and non-sensitive operational counts with partial-failure safety.
- 100% of Admin Operations access to system status remains staff-only and read-only.
- Cycle and decision registries expose status, domain, and current navigation without
  requiring a full-text read of every document.
- Every explicitly tracked compatibility bridge has a purpose and exit evidence, or
  is marked as intentionally durable.
- Product bets record a hypothesis, current evidence, next experiment, and signals
  to continue, reformulate, pause, or stop; target dates are optional.
- `manage.py check`, focused PCF regressions, architecture/privacy boundaries, and
  the complete Django suite pass at closure.

## Patch plan

### PCF00 · Cycle contract and baseline

- Record findings, boundaries, metrics, and staging gates.
- Add the cycle to the active-cycle index.
- Create the dedicated feature branch without touching local data artifacts.

### PCF01 · Integration branch control

- Align GitHub Actions with the documented `staging -> main` flow.
- Add migration-drift and accidental-artifact checks to the clean-environment gate.
- Preserve focused local validation and full integration validation.

### PCF02 · Environment contract and entrypoint parity

- Add a secret-free `.env.example` and typed environment metadata.
- Align WSGI and ASGI production defaults.
- Make invalid critical configuration visible instead of silently ambiguous.

### PCF03 · Environment diagnostics

- Add `diagnose_environment` with human and JSON output.
- Cover settings, database kind, Sites/OAuth shape, email, observability, AI rollout,
  and external food-source readiness without network calls or secret disclosure.
- Provide clear `ok`, `warning`, and `error` findings.

### PCF04 · Executable project status contract

- Build one application service for release, environment, migrations, capabilities,
  and safe operational aggregates.
- Add `project_status` human/JSON CLI surfaces.
- Degrade individual probes safely rather than failing the whole report.

### PCF05 · Read-only Admin Operations control plane

- Expose the project-status contract to staff in Admin Operations.
- Present attention items, deployment identity, migrations, integrations, and data
  health without adding mutation endpoints.
- Add staff access, rendering, and query-count-conscious tests.

### PCF06 · Documentation control registry

- Separate live navigation from completed-cycle history in the cycle index.
- Add machine-readable metadata extraction and validation for current docs, cycles,
  and decisions.
- Detect duplicate decision identifiers and invalid or missing statuses.

### PCF07 · Transition and artifact clarity

- Add a concise compatibility-transition registry with purpose, consumers, and exit
  evidence.
- Define an operational-artifact policy and stop new root-level reports/backups from
  entering version control.
- Preserve existing historical reports until an explicit cleanup decision.

### PCF08 · Outcome portfolio and foresight

- Add a small portfolio of product bets expressed as hypotheses and evidence.
- Track next experiments and continuation/reformulation signals, not deterministic
  feature sequences.
- Surface the portfolio through current docs and project status.

### PCF09 · AI project-context interface

- Provide a compact, sanitized structured context derived from the same registries
  and status service.
- Integrate it with export workflows or a dedicated CLI mode without creating a
  second source of truth.
- Test that secrets and private data cannot enter the payload.

### PCF10 · Global regression and handoff

- Run focused configuration, control-plane, docs, architecture, and privacy tests.
- Run the full repository CI command.
- Promote durable outcomes to `docs/00_current/`, record the accepted decision, and
  publish remaining risks and staging validation steps.

## Staging validation

1. Confirm the deployed commit appears in Project Control.
2. Confirm migrations report no unapplied application migrations.
3. Compare sanitized capability states against the staging environment configuration.
4. Validate Google OAuth shape and callback configuration without exposing client
   credentials or performing automated login.
5. Confirm Food Catalog totals and recent batches match Inventory & Quality.
6. Confirm non-staff access is rejected and no control-plane route accepts POST.
7. Push a documentation-only commit and a code commit to verify the intended CI gates.
8. Record any mismatch as product evidence and reformulate the relevant probe before
   treating the dashboard as authoritative.

## Go/no-go rules

Stop or reformulate a patch when it duplicates domain logic, exposes a secret or
private record, introduces a generic command executor, makes local development depend
on external services, reports inferred state as fact, or adds more maintenance burden
than the ambiguity it removes.
