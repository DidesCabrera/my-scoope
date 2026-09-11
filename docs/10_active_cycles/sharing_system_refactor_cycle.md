# Sharing System Refactor Cycle

Status: in progress
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
| SHR03 · DailyPlan snapshots | pending | Versioned privacy-safe adapter and create/revoke API. |
| SHR04 · Preview and web claim | pending | Public GET preview, explicit POST claim and auth continuation. |
| SHR05 · Inbox migration | pending | New Inbox projection, legacy backfill and compatibility. |
| SHR06 · Mobile sharing | pending | Share Sheet, copy link, deep links, OAuth continuation and mobile Inbox. |
| SHR07 · Web/email unification | pending | Common sharing surface and invitation adapter. |
| SHR08 · Share Cards | pending | Branded image/OG output derived only from snapshots. |
| SHR09 · Operations | pending | Abuse controls, retention and minimum funnel evidence. |
| SHR10 · Expansion/legacy retirement | pending | Entity adapters, data migration and removal of duplication. |
