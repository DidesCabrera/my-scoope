# Account deletion and retention policy

Status: current
Policy version: `account-deletion.v1`
Owner: `accounts`

## Product contract

An authenticated consumer can open account deletion from Profile, review the
consequences, confirm with the literal `ELIMINAR`, and re-authenticate with the
current password when the account has one. OAuth-only accounts do not invent a
password requirement.

The operation is atomic. It closes access immediately, revokes sessions and
credentials, removes personal nutrition data, and returns an identity-free
receipt. It cannot be undone from the product.

## Data treatment

| Treatment | Models/data | Outcome |
| --- | --- | --- |
| Erase | Profile, measurements, private foods, meals, daily plans, programs, calendarizations, notification subscriptions, comparisons, shares sent, AI chats/jobs/proposals, OAuth grants, social login bindings, commercial credits and entitlement projection | Rows are deleted; dependent rows follow their parent. |
| Anonymize | Django user, operational AI usage, email delivery attempts, staff audit events, accepted-share references, original-author references, catalog creator/reviewer references | Identity and payload fields are removed while non-identifying operational aggregates may remain. |
| Retain for legal evidence | Provider subscriptions, payments, billing events and tax documents | Rows remain linked to the inactive anonymous user tombstone so financial and tax evidence is not broken. |
| Retain as system/reference data | Plans, billing products, OAuth clients, sites, permissions and shared catalog authorities | They are not owned by one consumer account. |

The executable, exhaustive model registry lives in
`accounts.services.deletion.MODEL_RETENTION_POLICY`. A regression test fails if
a new concrete model is added without a deliberate classification.

## Financial boundary

Only the minimum billing graph needed to preserve payment and tax-document
integrity remains. The public account identity, email, names and usable password
are removed. Exact statutory retention periods and any provider-specific
cancellation workflow remain an external legal/accounting release gate; they
must be reviewed for each launch country and payment provider.

Deleting a My Scoope account does not itself cancel a subscription managed by
Apple or Google. The confirmation UI must keep that distinction explicit.

## Operational evidence

`AccountDeletionRecord` stores a random receipt identifier, policy version,
source and aggregate deletion/retention counts. It contains no user foreign key,
email, username or other direct identity.
