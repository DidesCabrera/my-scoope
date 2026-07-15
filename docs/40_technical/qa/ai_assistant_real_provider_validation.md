# AI Assistant real-provider UX validation

Status: active
Date: 2026-07-13
Applies to: CM24, staging, `ai_nutrition_intake`

## Purpose

Use this procedure after fake-provider invariant replays pass and before closing the LLM-native alignment cycle. It exercises the configured real provider with synthetic messages while preserving usage and credit observability.

The command does not persist chat history, profile changes or final nutrition entities. It disables reviewable proposal tools for the validation engine. Provider usage and credits are real.

## Preconditions

From the deployed staging environment confirm:

```text
AI_ASSISTANT_LLM_PROVIDER != fake
AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=true
AI_ASSISTANT_OPENAI_API_KEY configured when provider=openai
AI_ASSISTANT_OPENAI_MODEL configured
AI_ASSISTANT_OPENAI_BASE_URL configured
```

Use an existing staging user with enough AI credits. The report identifies the user only by internal ID.

## 1. List scenarios without making calls

```bash
python manage.py validate_ai_assistant_real_provider --list-scenarios
```

## 2. Run a small scenario first

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --scenario saludo_y_descubrimiento \
  --output cm24_saludo_report.json \
  --fail-on-hard-regression
```

## 3. Run the complete CM24 suite

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output cm24_real_provider_report.json \
  --fail-on-hard-regression
```

`--user-id <id>` may be used instead of `--user-email`.

The built-in suite currently makes seven user turns. Tool loops may produce more than seven provider HTTP calls. Review current credit availability before execution.

## 4. Read the result

Automated status:

```text
automated_checks_passed
hard_regression
```

A successful automated result still contains:

```text
manual_review_required: true
```

Review every transcript using the prompts embedded in the report. Record a concise disposition for each scenario:

```text
accepted
accepted_with_follow_up
rejected
```

For `accepted_with_follow_up`, create a separate narrow cycle or issue. Do not extend the global prompt with ad hoc rules unless the failure is demonstrably a shared provider-contract problem.

## 5. Operational verification

Confirm the report contains:

- one completed `AIUsageEvent` for each user turn;
- provider and model values in the event and, when available, mirrored safe turn metadata;
- completed status;
- token totals and estimated cost when pricing is configured;
- charged credits and ledger entries when credits are enabled;
- no deterministic fallback;
- safe tool names/statuses only.

The dedicated action type is:

```text
assistant.ai_nutrition_intake.cm24_validation
```

This allows the run to be located in Admin Analytics/Django Admin without mixing it with ordinary user turns.

## 6. Closure evidence

To close CM24, retain:

1. the JSON report;
2. the commit/patch version tested;
3. staging environment and configured provider/model;
4. automated gate result;
5. human disposition for every scenario;
6. any follow-up issues moved outside this alignment cycle.

Do not store API keys, raw provider payloads or screenshots containing unrelated user data in the evidence package.
## Interpreting the first live-run failure classes

Do not treat every failed check as the same kind of regression.

```text
AIUsageEvent completed + provider metadata missing
-> instrumentation/adapter mismatch; persisted event is authoritative

Assistant confirms facts or direction but NutritionBrief does not change
-> real tool-grounding regression

Tool result exists but assistant says tools are unavailable
-> real tool-result grounding regression

Card requested but only a text list appears
-> real object-presentation regression
```

After the CM24 calibration hotfix, rerun the full command and retain the new JSON report separately. Do not overwrite the first report; together they document the defect and the verified correction.

## Provider transport evidence after three live runs

The first three reports must remain separate evidence files. They isolated:

```text
first run  -> observability bridge + text-only state claims
second run -> malformed textual envelopes + missing tool requests
third run  -> nested strict JSON still unreliable for operational tool payloads
```

After decision 0112, tool operations must arrive as provider-native function calls. The report records:

```text
provider_native_tool_transport
provider_native_tool_calls
provider_text_parse_ignored_due_to_native_tools
contract_repair_attempted
final_incomplete_reason
```

`structured_provider_contract` now validates both channels: any tool result requires recorded native function-call transport, while the final visible response must still be complete and parseable. A bounded repair attempt remains observable.

Run the fourth report under a new filename; do not overwrite the three earlier reports.

## Interpreting the fourth live run

The fourth report validates the native function channel when it records native calls and corresponding tool results. Its remaining failure classes were narrower:

```text
User says “algo simple” but complexity_level remains empty
-> proposal-preference schema gap; complexity belongs in update_proposal_preferences

Native read tool and typed result exist, but provider follow-up fails
-> preserve tool evidence and use a bounded result-only local acknowledgement
```

A result-only acknowledgement is acceptable only after a validated tool execution. It must not infer nutrition state or choose the next question. The report should still expose the provider follow-up degradation metadata.

Run the fifth report under a new filename and retain all previous reports as evidence:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output cm24_real_provider_report_after_post_tool_resilience.json \
  --fail-on-hard-regression
```

## Interpreting the fifth live run

The fifth run can be considered a transport and resilience success when provider health, native calls, tool grounding, cards and usage all pass. A remaining case where visible text says “simple” but `complexity_level` is absent means the provider function schema is under-specified, not that My Scoope should parse the prose locally.

Decision 0114 exposes the supported `update_proposal_preferences.updates` fields as compact JSON Schema properties. Run the sixth report under a new filename:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output cm24_real_provider_report_after_explicit_preference_schema.json \
  --fail-on-hard-regression
```

## Interpreting the sixth live run

The sixth run demonstrated a successful native tool path but exposed two final contract issues:

```text
The provider calls update_proposal_preferences but omits complexity_level
-> optional best-effort function arguments are insufficient; use strict nullable fields

The next card-review turn is blocked before provider execution
-> disabled reviewable proposal tools are still present in the catalog and consume input context
```

Decision 0115 makes the proposal-update function strict while preserving partial updates through null stripping. It also removes proposal-category tools from provider requests whenever reviewable proposal execution is disabled. Do not solve either issue by parsing assistant prose or increasing the global input limit.

Run the seventh report under a new filename:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output cm24_real_provider_report_after_capability_scoped_strict_tools.json \
  --fail-on-hard-regression
```

## Interpreting the seventh live run

The seventh run removed the provider-catalog limit failure and passed the complete native tool/card path. If the card displays low complexity while the final `NutritionBrief` still reports `complexity_level=None`, inspect the server-side tool-result projector before changing prompts or schemas.

Decision 0116 adds `complexity_level` to `_apply_proposal_preferences_to_brief()` and preserves its source map. Run the eighth report under a new filename:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --output cm24_real_provider_report_after_complexity_state_sync.json \
  --fail-on-hard-regression
```

When this report has no hard regressions, complete the manual transcript questions and record the disposition before marking CM24 closed.
## Eighth live report and targeted UX closure

The eighth complete report passed all automated checks. Human review found repeated profile-source prompting in `cambio_de_direccion`. The transcript metadata showed `tool_followup_LLMProviderRequestError` after each successful proposal update, so the visible copy came from the local post-tool acknowledgement rather than the normal provider response.

Decision 0117 changes that fallback to `state_ack_only.v2`. It may summarize validated tool state but cannot ask a follow-up question or select the next intake field. The report adds the hard check `post_tool_fallback_pacing`.

After applying the correction, rerun only the affected scenario to limit provider usage:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --scenario cambio_de_direccion \
  --output cm24_real_provider_report_after_state_only_local_ack.json \
  --fail-on-hard-regression
```

Expected fallback wording is a concise state confirmation, for example:

```text
Perfecto. La propuesta queda como un programa semanal para bajar grasa, con 3 comidas al día.
```

The transcript must not repeat `Para seguir`, ask again whether to use the personal profile, or contradict “avancemos”. A passing targeted report plus explicit human approval closes CM24; another complete suite is not required because the preceding eighth report already passed every automated scenario.


## BA06 targeted behavioral gate

BA06 extends the existing live harness instead of introducing a second validation path.
Run the targeted behavioral scenarios on staging with one explicit test user:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email user@example.com \
  --scenario tema_externo_breve \
  --scenario capacidades_en_lenguaje_de_producto \
  --scenario referencia_ambigua_sin_tools \
  --scenario datos_agrupados_y_cards \
  --scenario cambio_de_direccion \
  --output ba06_real_provider_report.json \
  --fail-on-hard-regression
```

The JSON report exposes one of these gate states:

- `blocked_by_hard_regression`: at least one automated invariant failed;
- `awaiting_manual_review`: automated invariants passed, but transcript review is still required.

For manual disposition, review every prompt emitted in `manual_review_prompts` and record, outside the report, the reviewer, date, scenario and `approved` or `changes_requested`. Do not copy API keys, environment variables or provider credentials into the evidence.

## PT06 and BA07 targeted closure evidence

After the post-tool transport is healthy, revalidate the behavior that local acknowledgements previously masked:

```bash
python manage.py validate_ai_assistant_real_provider \
  --live \
  --user-email <staging-user-email> \
  --scenario ficha_conocida_sin_repreguntas \
  --scenario referencia_ambigua_sin_tools \
  --output pt06_real_provider_report.json \
  --fail-on-hard-regression
```

The profile scenario performs a preflight against the selected user's persisted ficha. Every available `weight_kg`, `height_cm`, `age_years` and `sex` fact becomes an exact brief and stability requirement; genuinely absent fields remain valid follow-up candidates. The report exposes both sets through `profile_fixture`, preventing a static fixture from treating missing profile data as a runtime regression.

Closure requires all of the following:

- `provider_followup_health` passes and no healthy tool turn uses local acknowledgement copy;
- every available profile fact remains stable and is not visibly re-asked in the same turn;
- the second profile answer names only information that is genuinely pending;
- `referencia_ambigua_sin_tools` executes zero reads, writes and cards;
- a reviewer records the manual disposition after reading both transcripts.

A passing targeted report closes behavioral evidence, but BA07 still requires the whole-project regression boundary from a fresh `full` export.
