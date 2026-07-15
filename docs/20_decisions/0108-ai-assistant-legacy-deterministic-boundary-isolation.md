# 0108 — AI Assistant legacy deterministic boundary isolation

Status: accepted
Date: 2026-07-13
Scope: nutrition-intake engine selection, typed conversation state, proposal readiness and LLM fallback behavior

## Context

The LLM-native alignment removed deterministic interview instructions from provider context and prompts, but the runtime still shared several legacy components:

- the deterministic engine class lived in the same module as the LLM engines;
- question-selection policy lived under `ai_assistant/application/`;
- every `NutritionIntakeResult` calculated `pending_field` and visible follow-up questions, including results rebuilt after LLM tool calls;
- proposal validation depended on a helper that returned user-visible question copy;
- unused regex guards and local acknowledgements remained beside the LLM runtime;
- the preview engine eagerly instantiated a deterministic baseline even when it would never be used.

Those components did not always change the visible reply, but they preserved a second conversational agenda inside LLM turns and made future regressions likely.

## Decision

Deterministic conversation policy and LLM state construction are separate runtime boundaries.

```text
Explicit deterministic engine
  -> semantic parsers
  -> pending_field
  -> deterministic question selection and acknowledgements

LLM preview / production engine
  -> user message and recent chat objects
  -> provider + typed tools
  -> tool-result synchronization
  -> state/cards/proposal readiness only
  -> no backend-owned next question
```

The deterministic engine now lives in:

```text
notas/application/ai_intake/deterministic_chat_engine.py
```

Its stage/question policy now lives in:

```text
notas/application/ai_intake/deterministic_policy.py
```

The old provider-adjacent module `ai_assistant/application/conversational_intake.py` is removed.

## State-only LLM result

`build_llm_intake_result_from_brief()` builds the result used by LLM turns and tool-result synchronization. It preserves:

- the canonical `NutritionBrief`;
- summary and completed fields;
- profile draft cards;
- proposal readiness;
- a technical count of required proposal fields.

It intentionally clears:

```text
pending_field
follow_up_questions
required_follow_up_questions
visible_follow_up_questions
```

A missing field can still make a proposal not ready, but it does not become a backend-selected conversational question.

The deterministic builder remains the default for the explicit deterministic flow so short contextual answers such as `188` can still be interpreted against the previous deterministic prompt.

## Validation without conversational copy

`required_proposal_fields()` is the shared technical validator. It returns canonical field identifiers and contains no visible wording.

Proposal creation and readiness checks use that field-level contract. Only deterministic conversation code maps a required field to a human question.

## Fallback boundary

Provider failures in LLM preview or production return a bounded technical message. They do not invoke the deterministic parser for the same user turn.

Metadata makes the boundary observable:

```text
conversation_policy = llm_tools | deterministic_runtime
llm_*_fallback_kind = technical_message | explicit_deterministic_engine
deterministic_runtime_invoked = true | false
```

The deterministic engine may still be selected explicitly when:

- `AI_ASSISTANT_CHAT_ENGINE_MODE=deterministic`; or
- production rollout policy blocks LLM execution and intentionally routes the whole turn to the deterministic engine.

That is an engine-selection decision, not co-authoring inside an LLM turn.

## Removed LLM-side conversational guards

Unused helpers that rewrote provider tone, detected repeated questions through regex phrases or built local state acknowledgements were removed from `chat_engine.py`.

The retained visible-text boundary is technical: it extracts human-readable content and prevents raw structured provider envelopes from reaching the chat. State normalization and list de-duplication also remain technical responsibilities.

## Consequences

- LLM turns cannot acquire `pending_field` or deterministic follow-up copy after tool synchronization.
- A provider outage cannot silently switch the same turn to a rule-based interview.
- Deterministic mode keeps its existing fallback capability and contextual short-answer parsing.
- Proposal readiness remains deterministic and server-owned without dictating the conversation.
- Runtime metadata can distinguish a technical provider failure from an explicit deterministic engine selection.
- Future cleanup can remove or replace deterministic mode without touching the LLM state contract.

## Validation contract

At minimum, this boundary must keep green:

```bash
python manage.py check
python manage.py test notas.tests.test_ai_intake_runtime_boundary -v 2
python manage.py test ai_assistant \
  notas.tests.test_ai_assistant_conversation_replay \
  notas.tests.test_ai_assistant_chat_engine \
  notas.tests.test_ai_intake_runtime_boundary \
  notas.tests.test_ai_intake_ai_assistant_cards \
  notas.tests.test_ai_intake_llm_profile_cards \
  notas.tests.test_ai_profile_tools \
  notas.tests.test_ai_preference_tools \
  notas.tests.test_ai_proposal_preference_tools \
  notas.tests.test_ai_proposal_tools \
  notas.tests.test_ai_proposal_from_draft_tools \
  notas.tests.test_ai_intake_llm_tool_state_sync \
  notas.tests.test_ai_intake_tool_led_regressions -v 1
```

## Related decisions

- `0099-ai-assistant-llm-native-tool-intake-runtime.md`
- `0103-ai-assistant-tool-contracts-over-prompt-overstructuring.md`
- `0105-ai-assistant-provider-context-simplification.md`
- `0106-ai-assistant-adaptive-prompt-response-policy.md`
- `0107-ai-assistant-invariant-based-conversation-replays.md`
