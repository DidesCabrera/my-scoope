# 0103 · AI Assistant tool contracts over prompt over-structuring

Status: accepted
Date: 2026-07-10

## Context

The AI Assistant client-memory/tool-oriented cycle exposed a product risk: improving the assistant by adding more prompt prohibitions, regex-like semantic cases or visible-message guards can make the experience worse.

The desired product role is not a deterministic questionnaire disguised as a chat. The assistant should behave like an AI operator over real My Scoope capabilities. It should interpret the user's language, ask naturally when information is useful, and fill product objects through tools.

Several tools will also be candidates for reuse outside the current chat surface, including MCP or other future AI clients. Tool contracts therefore need to be clean product capabilities, not private hacks for one prompt.

## Decision

My Scoope will prefer **LLM freedom through tool contracts** over prompt over-structuring.

The system should guide the LLM with:

- a clear role;
- concise product boundaries;
- allowlisted tools;
- typed input schemas;
- semantic field descriptions;
- server-side validation;
- safe draft/write approval boundaries;
- user-visible cards generated from tool results.

The system should avoid solving conversational quality by adding:

- long prompt lists of prohibitions;
- deterministic questionnaire order in LLM mode;
- regex/alias expansion as the main intake mechanism;
- visible-message rewrites that make the assistant sound robotic;
- duplicated rules outside tool contracts;
- provider-facing implementation details that invite unnecessary questions.

In LLM modes, the assistant should interpret user language and call tools with normalized values. My Scoope validates the tool call and synchronizes state. The code should not try to be a parallel semantic interpreter except as technical fallback or deterministic mode.

## Consequences

- Tool descriptions and schemas become the main place to explain field meaning.
- Runtime context should be concise and positive, not dominated by `do_not_*` flags.
- If a field is technical bookkeeping, it should usually remain internal instead of being exposed as something the assistant might ask the user to resolve.
- A user-provided weight in a proposal conversation is assumed to be the current weight for that proposal unless the user expresses uncertainty, contradicts prior data, or asks for historical tracking.
- Regression tests should use provider fakes to validate parser, tools, state sync, cards and visible-text boundaries before manual testing with real providers.
- MCP-facing and future AI-facing tools should be designed as stable product capabilities with reusable contracts.

## Current application

For AI nutrition intake:

- `update_profile_draft` should receive LLM-interpreted fields such as `weight_kg`, `height_cm`, `age_years`, `sex`, `activity_level` and `training_frequency`.
- `update_proposal_preferences` should receive normalized proposal fields such as `goal`, `requested_entity`, `meals_per_day` and macro/energy preferences.
- `update_preference_draft` should receive food and practical preferences.
- `ppk_weight_source` remains internal calculation/audit metadata. It should not be shown to the LLM as a user-facing pending fact.

## Related documents

- `0086-ai-assistant-tool-oriented-operator.md`
- `0098-ai-assistant-client-memory-cycle-closure.md`
- `0099-ai-assistant-llm-native-tool-intake-runtime.md`
- `0102-ai-assistant-scripted-replay-scenarios.md`
- `docs/00_current/features/ai_assistant/tool_oriented_client_memory.md`
