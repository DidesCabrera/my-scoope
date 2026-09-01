# Consumer Mobile API v1

Status: current
Base path: `/api/v1/`
Interface owner: `mobile_api`

## Contract

The consumer API is a versioned, screen-oriented interface over existing Django
application services. It does not reproduce nutrition, calendarization,
commercial or deletion rules inside transport code.

All product responses use:

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

Errors use the same envelope with `ok=false`, empty `data`, and a stable error
object containing `code`, `message` and `details`.

The generated source of truth is `mobile-v1.openapi.json`. CI regenerates the
schema in memory and fails when the committed contract drifts.

## Implementation navigation

The stable public contract is intentionally separated from domain ownership:

```text
mobile_api/api.py                         API composition root and legacy route facade
mobile_api/routes/<domain>.py             HTTP routes, auth/scopes and stable operation IDs
mobile_api/schema_domains/<domain>.py     request/response schemas owned by one domain
mobile_api/<domain>.py                    domain-facing payload and application coordination
mobile_api/tests/test_<domain>_api.py     owner, authorization and behavior contracts
mobile_api/schemas.py                     compatibility re-export facade during extraction
mobile_api/tests/test_api_v1.py           compatibility regression suite during extraction
```

Comparisons is the reference extraction. Its route registry lives in
`routes/comparisons.py`, its independent schemas in
`schema_domains/comparisons.py`, its comparison calculations/projections in
`comparisons.py`, and its endpoint tests in `tests/test_comparisons_api.py`.

When extracting another domain:

1. preserve every URL, response envelope, status code and auth/scope rule;
2. pin each moved OpenAPI `operation_id` to its existing public value;
3. mount the domain router from `api.py` without adding tags or metadata drift;
4. keep compatibility re-exports in `schemas.py` until all consumers migrate;
5. move tests rather than copying them, using `tests/base.py` for authenticated setup;
6. lower the facade budgets and add exact budgets for the extracted modules;
7. require `export_mobile_openapi --check` and focused domain tests before the full suite.

The preferred extraction order is Proposals, Calendarization, Libraries/Composition,
Account/Billing and Assistant. It follows cohesion and dependency depth: domains
with existing application services move before the composition-heavy library surface.

## Authentication

- Public clients use authorization code + mandatory PKCE S256.
- Mobile OAuth clients require an app-generated device identifier and a declared
  platform at token exchange.
- Access tokens expire after 15 minutes.
- Refresh tokens expire after 30 days and rotate on every use.
- Reuse of an already-rotated refresh token revokes the whole device session.
- A user can revoke one device without invalidating unrelated devices.
- Existing MCP/ChatGPT authorization-code clients keep their access-only flow.

Mobile scopes are `mobile:read`, `mobile:write` and `mobile:account`.

## Consumer vertical through CML06

The API exposes health, session, device revocation, profile, consumer onboarding,
account entitlements, active calendarized program, Today, weight history/write,
paginated food search, durable AI submit/poll and account deletion.

CML04 adds meal check-ins, derived adherence, program-context measurements,
periodic reviews, reminder settings/upcoming logical events and explicit decisions
for prepared future revisions. Check-ins are append-only; corrections preserve
history. Review summaries are frozen at creation. Revision approval revalidates
that all affected days are strictly future and unexecuted, and the client cannot
submit arbitrary before/after plan snapshots.

CML05 adds `POST /foods/label-captures` as a confirmation endpoint, not an OCR
endpoint. It accepts normalized values only after client review, enforces the
existing food-creation entitlement and creates a private, unverified,
solver-disabled food with an idempotent receipt. Photos and raw OCR text are not
part of the API contract.

CML06 adds `GET /subscriptions` and
`POST /subscriptions/apple/transactions`. The first returns the current effective
plan, independent provider evidence, a stable Apple account token and only active
server-configured Apple product identifiers. It intentionally omits price:
localized price and currency are StoreKit authority. The second accepts StoreKit
2's signed transaction JWS, requires `mobile:write`, verifies it server-side and
updates billing evidence before the native client may finish the transaction.
Nutritionist accounts receive no consumer purchase offer.

MCE02 completes the native lived-program boundary. An owned Program can be
activated with explicit confirmation for empty days and replacement of the current
calendarization. The API exposes the complete dated-day summary, owner-scoped day
detail, bounded historical calendarizations and pause/resume/cancel operations.
All mutations delegate to the existing calendarization commands; dated snapshots
remain the historical authority and the source Program is not rewritten.

MCE03 adds the owner-scoped proposal center through `GET /proposals`,
`GET /proposals/{proposal_id}` and explicit approve, reject, cancel and apply
actions. The detail response is a bounded mobile projection of targets,
validation, nutrition simulation, server-authorized actions and applied result;
it does not expose raw provider output as an executable client contract. Approval
never applies content. Application delegates to the established proposal commands,
requires acknowledgement for external subject context and returns a trusted Meal
or DailyPlan library identity.

MCE04 adds supported-kind metadata and owner-scoped selectable options through
`GET /comparisons/metadata` and `GET /comparisons/options/{kind}`. Dynamic
option rows carry the canonical entity-card projection: identity, structural
indicators, nutrition KPIs and the Food or Meal composition panel required by the
selected kind; library mutation actions are intentionally excluded. Dynamic
comparison uses `POST /comparisons/compare`; Food slots use the established 100 g
fallback, while Meals and DailyPlans reject quantities and can include PPK.
Programs are not an accepted kind. Slots are positional and may repeat the same
entity, which permits comparisons such as 100 g versus 200 g of one Food. The
response carries the same ordered metric blocks and relative bars as the web
viewmodel; calculations are not reproduced by the client.

Saved comparisons use `GET/POST /comparisons/saved` and
`GET/PUT /comparisons/saved/{comparison_id}`. Reads are owner-scoped and render the
frozen `snapshot_payload`; updates explicitly rebuild the snapshot through the
existing command. The editable ID/quantity payload remains distinct from the
historical names and metric values.

MCE05 adds owner-scoped Assistant history through `GET /ai/chats` and
`GET /ai/chats/{chat_id}`. These endpoints expose a bounded mobile message
projection, availability/credit context and any pending turn identity. They never
return the persisted `conversation_payload`, brief internals or provider response
metadata.

`POST /ai/turns` and `GET /ai/jobs/{job_id}` remain the durable submit/poll
boundary. One pending turn is allowed per new-chat or existing-chat lane. A
completed job response verifies ownership and returns only the persisted `chat_id`
and refresh state; the client then reloads the trusted chat detail. The same
idempotency key cannot create another job, and a different key while the lane is
busy receives `assistant_turn_pending`.

MCE06 extends each bounded message with a discriminated `cards` union. Only
whitelisted presentation fields are projected for profile/preference/proposal
drafts, proposal review, generated plans, saved comparisons and prepared actions;
unknown persisted objects remain non-interactive. Proposal and comparison cards
open their trusted mobile detail surfaces.

Prepared mutations use `POST /ai/prepared-actions/{action_id}/commit` or
`POST /ai/prepared-actions/{action_id}/cancel`. Both require the mobile write
scope and resolve the opaque action against the authenticated owner. Commit also
rechecks expiration and the target snapshot before applying the existing command;
the mobile client sends no mutation arguments and reloads the conversation after
the result.

MCE07 allows `POST /ai/turns` to receive an optional owner-scoped
`comparison_id`. The API resolves the saved snapshot, sends only bounded product
context to the Assistant runtime and persists a typed comparison card in the
resulting conversation. A missing or foreign comparison fails closed as
`saved_comparison_not_found`; the message remains independent from the attached
object and no client-provided comparison payload is trusted.

## Native composition pickers

The library detail journey exposes dedicated preview/commit pairs for the four
composition operations available in the responsive web product:

- Food into an owned Meal, including a positive gram portion;
- an owned reusable Meal into an owned DailyPlan, including hour and optional
  note;
- an owned reusable DailyPlan into one or more days of an owned Program week;
- one new empty week at the end of an owned Program.

Preview endpoints are read-scoped and return server-computed selection nutrition,
before/after impacts and structural metrics. Commit endpoints require
`mobile:write` and delegate to the established Meal, DailyPlan and Program
commands. Meal and DailyPlan insertion preserve the existing snapshot semantics.
Assigning a DailyPlan reports occupied days during preview and rejects commit
with `picker_replacement_confirmation_required` until the client explicitly
confirms replacements. Adding a week increases duration and creates seven empty
slots; it does not create a parallel Week aggregate. The native creation flow
passes the previewed `expected_week_number` when committing, making a retry return
the already-created week instead of appending a duplicate.

## Native library creation

The four personal libraries accept owner-scoped creation through `POST` on their
existing collection routes: `/library/foods`, `/library/meals`,
`/library/daily-plans` and `/library/programs`. Every mutation requires
`mobile:write` and delegates to the same application commands used by the web
product.

Food creation receives a name and protein, carbohydrate and fat values per 100 g
and immediately returns a complete Food detail. Meal, DailyPlan and Program
creation receives a name and returns an owned draft detail so the native client
can continue directly into composition. Adding the first Food completes a Meal;
adding the first Meal completes a DailyPlan; assigning the first DailyPlan
completes a Program.

Meal and DailyPlan collection reads keep their reusable-only behavior by default.
The native personal-library screens opt into `include_drafts=true`, which exposes
only the authenticated owner's resumable drafts and labels them explicitly as
`Borrador`. Composition pickers continue using the default query and therefore
never offer incomplete drafts as source selections.

## Native comparison edit panels

Owned library details expose the same edit surface as the responsive comparison
panels. Their mutation routes require `mobile:write`, verify the parent and child
relationship against the authenticated owner, and delegate to the existing
composition commands:

- Meal food rows can update portion, delete, and save a complete relation order;
- DailyPlan meal rows can update schedule metadata, delete, save order, or pass
  `dailyplan_meal_id` through the meal picker to replace the existing slot;
- Program weeks can be reordered, duplicated, or removed while preserving at
  least one week;
- Program day rows can remove an assigned DailyPlan, while add and replace keep
  using the DailyPlan picker and its replacement confirmation.

Relation identifiers are projected explicitly as `relation_id`; aggregated food
rows remain read-only because they do not identify a single editable relation.
Shared Programs expose the comparison data but not owner-only mutations.

Native notification delivery remains CML07; the API already exposes the common
calendarization schedule that each channel must follow. Future library edits must
preserve the same envelope, scopes, snapshot rules and service boundaries.
