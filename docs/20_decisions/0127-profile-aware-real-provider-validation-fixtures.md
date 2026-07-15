# 0127 — Profile-aware real-provider validation fixtures

Status: accepted
Date: 2026-07-14
Cycle: PT06 corrective validation

## Context

The first live PT06 run used an existing staging account whose persisted ficha
contained weight and height, but not birth date/derived age or sex. The
assistant correctly reported age, sex and activity as pending. The release gate
nevertheless failed because the scenario had hard-coded weight, height, age and
sex as facts that must always be captured.

That mixed two different concerns:

- whether the runtime preserves every fact actually returned by the profile
  tool; and
- whether a particular staging user has completed every onboarding field.

An incomplete validation fixture is not itself a conversational regression.
Conversely, simply dropping the profile assertions would hide a real state-sync
regression when those facts do exist.

## Decision

- Before running `ficha_conocida_sin_repreguntas`, read the selected user's
  persisted nutrition profile through the same domain query used by the profile
  tool.
- Add every available profile fact to the scenario's exact expected brief and
  stable-fact contract.
- Do not require genuinely absent profile facts; the assistant may correctly
  ask for them.
- Continue watching weight, height, age and sex for redundant questions once
  any of them becomes known during the conversation.
- Emit a diagnostic `profile_fixture` check and serialize the available/missing
  preflight fields in the JSON report.

## Consequences

The gate is now strict about runtime behavior and explicit about fixture
completeness. A complete ficha still proves that all four facts cross the tool
boundary into `NutritionBrief`; an incomplete ficha no longer creates a false
hard regression merely because the assistant names truly pending data.
