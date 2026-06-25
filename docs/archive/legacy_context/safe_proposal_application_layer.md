# Safe Proposal Application Layer

## Purpose

The Safe Proposal Application Layer defines how an approved nutrition proposal can be safely applied to real user data.

Its main purpose is to prevent AI, MCP tools, API clients or raw JSON payloads from directly mutating core models such as DailyPlan, Meal, MealFood or Food.

Instead, proposals must go through a strict application pipeline:

```text
NutritionProposal approved
  → parse proposed_payload
  → validate allowed operations
  → apply through internal commands
  → mark proposal as applied
  → record audit event