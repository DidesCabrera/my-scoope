# Sharing

Sharing is being migrated from entity-specific email records to a product capability
with four separate responsibilities: resource, invitation, claim and Inbox delivery.

The accepted target contract is recorded in Decision 0193. During migration, the
existing `DailyPlanShare`, `ProgramShare`, `MealShare`, `FoodShare` and
`DailyPlanMealShare` flows remain supported.

## Target rules

- A share exposes a versioned snapshot, never the private source object.
- A public GET is preview-only.
- Claim is an authenticated, explicit and idempotent write.
- Directed invitation identity and link possession are separate checks.
- Inbox is independent from delivery channel.
- Saving creates a recipient-owned copy.

Implementation progress and transition evidence live in
`docs/10_active_cycles/sharing_system_refactor_cycle.md`.

## Current vertical

The normalized core and the first DailyPlan adapter are available. Authenticated
mobile clients can create an unlisted resource and revoke one they own. The stored
snapshot contains only its title, aggregate nutrition, meal times and food
composition; it excludes account identity, source IDs and free-form notes. Later
source edits do not rewrite an existing share.

The unlisted `/s/<public-id>/` page renders only the stored snapshot and sends
`noindex`/`no-store` protections. Opening it never claims content. Claim is a
CSRF-protected POST; anonymous intent survives login, but the returning GET still
requires explicit confirmation. Claims are idempotent and create one normalized
Inbox item. Directed invitations additionally require a matching verified email.

Inbox now reads normalized deliveries and unmigrated legacy records together. An
idempotent migration converts accepted legacy DailyPlan shares, preserves read,
favorite and dismissed state, and suppresses the corresponding legacy projection.
Other legacy entity types remain on their compatibility path until their snapshot
adapters exist. A recipient can save a claimed DailyPlan as one detached,
recipient-owned library copy; revoking the public URL does not erase an already
claimed private Inbox snapshot.

## Mobile channels

DailyPlan actions in the native app now create the same portable resource for both
the operating-system Share Sheet and explicit copy-link. Other entity types retain
their email compatibility form until they receive snapshot adapters. Public pages
offer the registered `myscoope://share/<id>` deep link; the native share screen can
render before login and preserves its destination through OAuth, disclosures and
onboarding. Native Inbox lists normalized claims and supports read, favorite,
dismiss and idempotent save-to-library actions.

## Web and email channels

The DailyPlan web share page now exposes one sharing surface: it can create and copy
an unlisted link or send a directed email invitation over the same immutable
`ShareResource`. The latest active resource is reused while its snapshot and claim
policy remain current; editing the source causes the next action to create a new
snapshot without mutating old links.

Directed email uses a `ShareInvitation` with its own unguessable `/i/<public-id>/`
preview. The email channel stores only invitation content and delivery lifecycle;
opening it remains read-only, and claiming requires a matching verified account plus
an explicit POST. Both `/s/` and `/i/` bypass nutrition onboarding so the preview and
authentication continuation remain reachable. The legacy mobile library email action
for DailyPlan also delegates to this normalized path; other entity types stay on the
compatibility implementation until their adapters are added in SHR10.
