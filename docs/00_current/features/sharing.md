# Sharing

Sharing is a product capability independent from entity-specific email records,
with four separate responsibilities: resource, invitation, claim and Inbox delivery.

The accepted contract is recorded in Decision 0193. Historical
`DailyPlanShare`, `ProgramShare`, `MealShare`, `FoodShare` and
`DailyPlanMealShare` tables remain only for rollback and old-token compatibility;
active product flows do not write them.

## Target rules

- A share exposes a versioned snapshot, never the private source object.
- A public GET is preview-only.
- Claim is an authenticated, explicit and idempotent write.
- Directed invitation identity and link possession are separate checks.
- Inbox is independent from delivery channel.
- Saving creates a recipient-owned copy.

Implementation progress and transition evidence live in
`docs/10_active_cycles/sharing_system_refactor_cycle.md`.

## Entity adapters

Food, Meal, DailyPlan, DailyPlanMeal and Program use explicit snapshot adapters.
Snapshots contain only the portable title, nutrition and required composition;
they exclude account identity, source IDs and free-form notes. A DailyPlanMeal is
represented as the Meal subject with a `daily_plan_meal` variant. Program snapshots
nest detached DailyPlan snapshots for planned days. Later source edits never rewrite
an existing share.

The unlisted `/s/<public-id>/` page renders only the stored snapshot and sends
`noindex`/`no-store` protections. Opening it never claims content. Claim is a
CSRF-protected POST; anonymous intent survives login, but the returning GET still
requires explicit confirmation. Claims are idempotent and create one normalized
Inbox item. Directed invitations additionally require a matching verified email.

Inbox reads normalized deliveries and uses legacy records only as a pre-migration
fallback. Migration 0060 converts pending and accepted historical shares for every
entity, preserves the original token, recipient, message and Inbox state, and is
idempotent. Saving hydrates one detached recipient-owned Food, Meal, DailyPlan or
Program copy. Revoking a public URL does not erase an already claimed Inbox snapshot.

## Mobile channels

Every supported library entity in the native app creates the same portable resource
for the operating-system Share Sheet, explicit copy-link and protected email. Public pages
offer the registered `myscoope://share/<id>` deep link; the native share screen can
render before login and preserves its destination through OAuth, disclosures and
onboarding. Native Inbox lists normalized claims and supports read, favorite,
dismiss and idempotent save-to-library actions.

## Web and email channels

All web share forms send directed email invitations over immutable normalized
resources; DailyPlan additionally exposes explicit link creation. The native app
offers native sharing and copy-link for every entity. The latest active resource is
reused while its snapshot and claim policy remain current; editing the source causes
the next action to create a new snapshot without mutating old links.

Directed email uses a `ShareInvitation` with its own unguessable `/i/<public-id>/`
preview. The email channel stores only invitation content and delivery lifecycle;
opening it remains read-only, and claiming requires a matching verified account plus
an explicit POST. Both `/s/` and `/i/` bypass nutrition onboarding so the preview and
authentication continuation remain reachable. Old accept-route names remain valid,
but GET only redirects to this preview and never claims content.

## Snapshot share cards

Active public resources and directed invitations expose branded 1200×630 PNG cards
for Open Graph and large Twitter previews. The renderer is deterministic and accepts
only the stored snapshot: it has no request, model or source-object access. Card
responses use a snapshot-derived ETag, a five-minute public cache and return 404 as
soon as the resource or invitation is no longer active.

The directed invitation page points to an invitation-scoped card URL and omits the
resource deep link, preventing its HTML metadata from weakening the verified-email
claim boundary. Titles and numeric values are normalized and bounded before drawing;
the rendering dependency and Unicode-capable platform font fallbacks are explicit.

## Operations

New resources expire after a configurable 30-day TTL. Daily maintenance expires due
resources and invitations and deletes only old revoked/expired resources without a
claim; claimed Inbox snapshots survive. Shared-cache limits protect public rendering,
claim attempts and per-user creation, while email keeps its additional recipient and
budget controls.

The Product Activity dashboard derives a privacy-minimal normalized funnel from
resources, aggregate preview counters, invitations, claims and saved Inbox copies.
No visitor IP or user-agent is retained. Apple Universal Links and Android App Links
are declared for production `/s/*`; server association endpoints return 503 until the
real Apple Team ID and Android signing fingerprints are configured. Directed `/i/*`
invites remain web-only so native routing cannot bypass verified-email enforcement.
Deployment, verification and incident steps live in
`docs/40_technical/operations/sharing_operations_runbook.md`.
