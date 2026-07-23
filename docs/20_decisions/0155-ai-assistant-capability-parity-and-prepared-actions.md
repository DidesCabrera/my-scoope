# Decision 0155: AI Assistant capability parity uses one catalog and prepared actions

Status: accepted
Date: 2026-07-23

## Context

My Scoope exposed a useful but partial assistant: the provider-facing registry and
standalone MCP registry repeated capability declarations, several existing read
queries were not reachable from chat, and product mutations had only two safety
patterns—nutrition proposals and the profile-specific approval button.

The target is not unrestricted model autonomy. It is product capability parity:
the assistant should understand every user-facing area, read authorized state and
either create a reviewable proposal, prepare a confirmable action, or hand the user
to the existing trusted UI when external or specialized controls must remain there.

DailyPlan meals are independent snapshots. Quantity changes inside those snapshots
must not mutate the reusable Meal from which they were copied.

## Decision

`ai_assistant.application.tools.registry` is the canonical executable tool catalog.
Provider declarations and the standalone MCP server are projections of that catalog;
MCP may expose a governed subset and may retain compatibility names.

Name-based work first uses bounded list/search/read tools. A model never invents an
identifier and every query applies the existing visibility or ownership boundary.
Provider tool declarations are selected by product domain per turn so the expanded
catalog stays inside technical context limits.

Nutrition mutations remain `NutritionProposal`-first. The proportional DailyPlan
calorie operation:

- resolves an owned DailyPlan;
- computes a single linear scale factor;
- emits one `update_meal_food_quantity` operation per snapshot MealFood;
- preserves food identities and meal structure;
- changes nothing until the existing approve/apply workflow runs.

General supported mutations use `AIPreparedAction`. Preparation persists only an
audit/preview record with a before snapshot, after preview, expiry and target
fingerprint. A provider cannot call the commit capability. Commit is reachable only
from authenticated CSRF-protected UI actions, locks the record, rechecks ownership
and fingerprint, rejects stale/replayed/expired actions, then delegates to existing
application commands.

Billing checkout/cancellation stay in billing UI and never run from a model tool.
Administrative analytics and operations remain staff-only and outside the end-user
catalog.

## Consequences

- AI and MCP declarations cannot drift independently.
- The assistant can resolve Foods, Meals, DailyPlans, Programs, calendarization,
  proposals, comparisons, Inbox and account/billing context.
- Basic entity, program, calendar and proposal lifecycle operations have a common
  prepare-preview-confirm-commit contract.
- Specialized composition, sharing/import, checkout and staff operations remain
  explicit trusted-UI handoffs rather than hidden gaps or unsafe generic writes.
- A concurrent human change invalidates a prepared action instead of being silently
  overwritten.
- Rollout flags still govern use of the LLM and reviewable tools; this decision does
  not bypass the existing production rollout gate.
