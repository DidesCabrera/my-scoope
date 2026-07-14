# 0109 · AI Assistant real-provider UX validation gate

Status: accepted
Date: 2026-07-13
Scope: AI Assistant nutrition chat, staging validation, usage/credit observability

## Context

CM19-CM23 aligned the nutrition assistant around an LLM-led, tool-oriented runtime:

- draft updates are silent and cards are shared explicitly;
- provider context exposes current objects instead of a duplicated questionnaire;
- prompts use adaptive conversational principles rather than fixed order or question count;
- fake-provider replays protect state, tools, cards, visible-text and persistence invariants;
- the legacy deterministic interviewer is isolated from LLM turns and provider failures.

Those automated checks cannot prove that a real configured model feels natural. A provider may satisfy schemas while still producing repetitive questions, awkward acknowledgements, poor card pacing or unhelpful tool-error recovery. Conversely, exact-copy tests would freeze one conversation and recreate the over-structuring problem.

CM24 therefore requires a controlled staging run that combines automated runtime invariants with explicit human UX review.

## Decision

Add an explicit management command for real-provider validation:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output cm24_real_provider_report.json \
  --fail-on-hard-regression
```

The command must never run live calls without `--live`. It requires:

- one existing authenticated staging user;
- a configured non-fake provider;
- usage observability enabled.

The validation engine calls the configured provider directly through the LLM preview runtime, regardless of the public rollout mode, and marks every turn with a dedicated CM24 action type. Reviewable proposal tools are disabled during the validation run so the script can exercise drafts, reads, cards and readiness without creating proposals or final nutrition objects.

## Built-in scenarios

The controlled suite covers:

1. natural greeting and task discovery;
2. grouped profile/proposal facts and explicit card sharing;
3. changes of goal and requested entity;
4. a safe `read_proposal` not-found result and conversational recovery.

Synthetic values are used. The JSON report contains the synthetic transcript, typed brief snapshots, safe tool names/statuses, card deltas, provider/model, usage events and credit totals. It does not include API keys, headers, raw provider payloads, tool data payloads or real profile fields.

## Automated hard invariants

The command fails its automated gate when it detects any of the following:

- empty visible output or provider-envelope/internal-state leakage;
- deterministic runtime invocation during a live LLM turn;
- technical fallback or fake/missing provider identity;
- loss of grouped facts or expected intent transitions;
- known captured fields reintroduced as `missing_slots`;
- missing required tool calls or missing expected tool-error result;
- draft updates rendering cards without explicit share tools;
- duplicated/excess cards outside scenario bounds;
- missing or non-completed `AIUsageEvent` records.

Only bounded semantic metadata is added to the chat-engine result for this purpose:

```text
llm_semantic_intent
llm_semantic_missing_slots
llm_tool_results = [{tool_name, status, optional error_code}]
```

Tool data and error messages are intentionally omitted.

## Human UX gate

Passing automated invariants is necessary but not sufficient. A human must review the transcript for:

- natural greeting and task discovery;
- unnecessary repeated questions;
- acknowledgement quality;
- grouping of related questions;
- card timing and textual redundancy;
- acceptance of intent changes;
- tool-error recovery in user language;
- overall usefulness and tone.

The report explicitly remains `manual_review_required=true`. CM24 and the LLM-native alignment extension may be marked completed only after one staging report passes the hard gate and the human review is recorded.

## Consequences

- Real provider calls and credits are always explicit and attributable to a dedicated action type.
- Validation evidence becomes reproducible instead of being scattered across screenshots or informal chat notes.
- The command does not judge naturalness through another LLM and does not introduce new prompt rules.
- UX findings should become narrow product/tool fixes. They must not automatically trigger more global prohibitions or questionnaire logic.
- CM24 implementation prepares the closure gate; it does not falsely claim that the provider has already been validated.
## Live calibration amendment

The first real-provider run demonstrated that provider health and usage must not depend solely on one chat-adapter metadata bridge. Completed non-fake `AIUsageEvent` rows matched by turn are the hard evidence; safe provider/model/usage metadata remains a diagnostic mirror.

The run also confirmed a separate product invariant: visible acknowledgements cannot substitute for draft/read/share tools. This operational boundary is recorded in `0110-ai-assistant-tool-grounded-state-claims.md`. A second live report is required after applying that calibration.
