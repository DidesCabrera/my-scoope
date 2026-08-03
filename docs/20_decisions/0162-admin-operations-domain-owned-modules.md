# Decision 0162: Admin Operations modules are owned by operational domain

Date: 2026-08-02
Status: accepted
Cycle: TDG04

## Context

Admin Operations grew from a small staff overview into a control plane for Food
Catalog, accounts and credits, AI operations and audit. Its service module exceeded
2,500 lines and selectors/view models also mixed every operational domain. Food
Catalog accounts for most of that growth because it is now strategically important;
its surface must remain prominent and complete.

## Decision

Organize services, selectors and view models into domain-owned modules for:

- overview;
- Food Catalog;
- accounts and credits;
- AI Assistant;
- audit.

Keep the historical `services`, `selectors` and `viewmodels` modules as thin
compatibility facades. Existing callers therefore retain their public imports while
new implementation work has an explicit owner.

Food Catalog remains the largest owned service module. This reflects its real
curation, import, observability, publication and snapshot responsibilities and is
not treated as accidental scope to remove.

Application modules raise an interface-neutral target-not-found exception. The HTTP
interface translates it to a 404 and owns Django messages, so domain services no
longer import HTTP shortcuts or message APIs.

## Consequences

- The compatibility service facade is 12 lines instead of more than 2,500.
- Accounts, AI, audit and overview can evolve and be tested without editing the Food
  Catalog implementation file.
- Selector and view-model facades are similarly thin while the real definitions are
  grouped by domain.
- The HTTP-import allowlist for Admin Operations application modules is empty and is
  enforced by the architecture test.
- Future Food Catalog decomposition can follow its internal workflow boundaries
  without weakening its product or operational role.
