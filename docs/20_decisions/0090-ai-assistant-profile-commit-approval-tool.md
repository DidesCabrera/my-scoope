# 0090 — AI Assistant profile commit approval tool

Status: accepted
Date: 2026-07-09

## Context

CM03 introduced non-persistent profile draft tools and CM04 rendered profile draft cards inside the chat thread. That allowed the LLM to help complete a structured ficha for the current conversation without silently changing persistent user data.

The next boundary is approval. A profile card can show values captured from chat, but updating the user's persistent ficha must be a product action initiated by the user, not a free-form LLM decision.

## Decision

My Scoope adds an internal commit tool:

```text
commit_profile_update
```

This tool is part of the AI Assistant tool registry, but it is not exposed to the LLM provider. It may only execute when My Scoope attaches trusted server-side approval metadata from an explicit user action, such as the profile card button in the chat UI.

The commit tool can persist only fields that the current data model can safely store:

```text
weight_kg -> WeightLog
height_cm -> Profile.height_cm
sex -> Profile.sex
```

Fields such as `age_years`, `activity_level` and `training_frequency` remain conversation/proposal context until the product has dedicated profile, body-state or preference objects for them.

## Consequences

The LLM can keep acting as an assistant that fills drafts through tools, but it cannot directly persist profile memory.

The UI approval button now routes through the same tool boundary instead of bypassing the tool system with view-only custom write logic.

The provider-facing tool list excludes `commit_profile_update`, so the model should not attempt to call it. If a provider response invents that tool name, execution is still blocked unless the server-side `approved_by_user` and `approval_source` metadata are present.

This reinforces the product rule:

```text
LLM interprets and prepares.
My Scoope validates, renders and persists only after explicit user approval.
```

CM06 should continue with preference draft tools for avoided foods, preferred foods and meal organization preferences.
