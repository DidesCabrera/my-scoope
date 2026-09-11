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
