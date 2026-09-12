# Sharing System Refactor Cycle

Status: completed
Date: 2026-09-11
Cycle code: SHR

## Objective

Replace channel- and entity-coupled sharing with a secure product capability that
creates portable snapshots, distributes them through independent channels, preserves
authentication context, records idempotent claims and delivers product objects to a
channel-independent Inbox.

## Invariants

- Opening a URL never performs a claim.
- Directed invitations require the authenticated user's verified email to match.
- Tokens are unguessable credentials but never replace authorization checks.
- Public previews render only immutable, versioned and privacy-reviewed snapshots.
- Source objects remain private and are never read through a public token.
- Claims are idempotent and cannot overwrite another recipient.
- Inbox state belongs to the recipient, not to email delivery.
- Saving to the library creates a user-owned copy.
- Legacy URLs and email remain compatible until their data is migrated.
- Channel adapters do not own sharing-domain rules.

## Patch sequence

| Patch | Status | Exit evidence |
| --- | --- | --- |
| SHR00 · Architecture contract | completed | Decision 0193, stable vocabulary, 22 focused tests and dependency guard. |
| SHR01 · Legacy safety baseline | completed | Recipient-bound idempotent claims, Program acceptance and 29 focused tests. |
| SHR02 · Sharing core | completed | Four normalized models, migration 0056, lifecycle services and 27 focused tests. |
| SHR03 · DailyPlan snapshots | completed | Privacy-limited immutable adapter, owner-only create/revoke API and generated OpenAPI contract. |
| SHR04 · Preview and web claim | completed | Unlisted snapshot preview, POST-only idempotent claim, verified directed identity and safe login continuation. |
| SHR05 · Inbox migration | completed | Dual normalized/legacy projection, idempotent DailyPlan backfill and detached save-to-library. |
| SHR06 · Mobile sharing | completed | Native Share Sheet/copy-link, scheme deep link, OAuth continuation and normalized mobile Inbox. |
| SHR07 · Web/email unification | completed | One DailyPlan web surface for reusable links and directed email; normalized invitation lifecycle and mobile compatibility action. |
| SHR08 · Share Cards | completed | Deterministic 1200×630 PNG cards, Open Graph/Twitter metadata, bounded cache and revocation behavior from snapshots only. |
| SHR09 · Operations | completed | Shared-cache abuse limits, 30-day expiry/retention job, privacy-minimal funnel evidence and fail-closed mobile association endpoints. |
| SHR10 · Expansion/legacy retirement | completed | Food, Meal, DailyPlanMeal and Program adapters; detached save for all subjects; idempotent token-preserving backfill; unified web/mobile channels and snapshot-only source reads. |

## Closure

All supported nutrition entities now use `ShareResource`, `ShareInvitation`,
`ShareClaim` and `InboxItem`. Legacy rows are retained only as rollback-compatible
storage: migration 0060 projects every historical row into the normalized model,
old token URLs redirect to the read-only invitation preview, and active channels,
badges, workspace reads and analytics no longer write or count the legacy tables.

Closure evidence: 1,914 Django tests, 85 native tests, native lint/typecheck, the
97-test fast architecture gate, migration drift, OpenAPI drift, repository hygiene
and the strict document registry all pass.
