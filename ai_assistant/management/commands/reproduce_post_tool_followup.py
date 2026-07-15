from __future__ import annotations

import json
from dataclasses import replace

from django.core.management.base import BaseCommand, CommandError

from ai_assistant.application.orchestrator import ExternalLLMOrchestrator
from ai_assistant.domain import (
    AssistantMessage,
    AssistantMessageRole,
    AssistantToolResult,
    AssistantToolStatus,
    AssistantTurnRequest,
)
from ai_assistant.infrastructure.providers.contracts import (
    LLMProviderRequest,
    LLMProviderRequestError,
)
from ai_assistant.infrastructure.providers.factory import get_llm_client
from ai_assistant.infrastructure.providers.openai_client import build_openai_responses_payload

PROBE_USER_MESSAGE = (
    "Quiero un plan diario para bajar grasa con 4 comidas. "
    "Registra esa dirección para la propuesta."
)


class Command(BaseCommand):
    help = (
        "PT02: reproduce the real orchestrator post-tool follow-up against the "
        "configured provider and print the preserved provider error (PT01). "
        "This makes real provider calls and consumes usage."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Required. Confirms real provider calls (and cost) are intended.",
        )
        parser.add_argument(
            "--provider",
            default=None,
            help="Provider override. Defaults to AI_ASSISTANT_LLM_PROVIDER (target: openai).",
        )
        parser.add_argument(
            "--no-strict",
            action="store_true",
            help="Use the same JSON Schema with strict=false on the follow-up.",
        )
        parser.add_argument(
            "--no-tools",
            action="store_true",
            help="Remove the tool catalog from the follow-up.",
        )
        parser.add_argument(
            "--no-reasoning",
            action="store_true",
            help="Remove reasoning configuration and reasoning continuation items.",
        )
        parser.add_argument(
            "--show-payload",
            action="store_true",
            help="Print the exact OpenAI payload produced by the production payload builder.",
        )

    def handle(self, *args, **options):
        if not options["live"]:
            raise CommandError(
                "PT02 makes real provider calls. Re-run with --live once you accept the usage cost."
            )

        client = get_llm_client(provider_name=options.get("provider"))
        provider_name = getattr(client, "provider_name", "unknown")
        self.stdout.write(f"provider: {provider_name}")
        if provider_name == "fake":
            raise CommandError(
                "Provider is 'fake'; it cannot validate the real Responses transport. "
                "Set AI_ASSISTANT_LLM_PROVIDER=openai or pass --provider openai."
            )

        orchestrator = ExternalLLMOrchestrator(llm_client=client)
        turn_request = AssistantTurnRequest(
            user_message=AssistantMessage(
                role=AssistantMessageRole.USER,
                content=PROBE_USER_MESSAGE,
            ),
            context={"surface": "ai_nutrition_intake"},
            metadata={
                "action_type": "assistant.post_tool_followup_probe",
                "surface": "ai_nutrition_intake",
            },
        )

        # Use the production orchestrator builder: full prompts, strict response
        # schema and the real tool catalog. The previous probe used a reduced
        # schema/tool declaration and could pass while the product request failed.
        first_request = orchestrator.build_provider_request(turn_request)
        try:
            first_response = client.generate(first_request)
        except LLMProviderRequestError as exc:
            self._print_provider_error("first_call", exc)
            raise CommandError("First probe call failed; see error above.") from exc

        tool_calls = tuple(first_response.tool_calls or ())
        self.stdout.write(f"first_call.tool_calls: {len(tool_calls)}")
        if not tool_calls:
            self.stdout.write(
                self.style.WARNING(
                    "The model did not emit a function call, so the follow-up cannot be "
                    "tested. Re-run once; models can vary between calls."
                )
            )
            return

        call = tool_calls[0]
        if not call.call_id:
            raise CommandError(
                "The provider returned a function_call without call_id. Production cannot "
                "correlate a function_call_output for this response."
            )
        self.stdout.write(f"first_call.function: {call.name} call_id={call.call_id}")

        tool_result = AssistantToolResult(
            tool_name=call.name,
            status=AssistantToolStatus.OK,
            request_id=call.call_id,
            data=_probe_result_data(call.name),
            metadata={"probe": "post_tool_followup_transport.v2"},
        )
        followup_request = orchestrator.build_tool_followup_provider_request(
            request=turn_request,
            continuation_items=first_response.continuation_items,
            tool_results=(tool_result,),
            remaining_tool_iterations=max(orchestrator.config.max_tool_loop_iterations - 1, 0),
        )
        followup_request = _apply_variant(
            followup_request,
            strict=not options["no_strict"],
            with_tools=not options["no_tools"],
            with_reasoning=not options["no_reasoning"],
        )

        strict = not options["no_strict"]
        with_tools = not options["no_tools"]
        with_reasoning = not options["no_reasoning"]
        self.stdout.write("")
        self.stdout.write(
            "followup variant: "
            f"strict={str(strict).lower()} tools={str(with_tools).lower()} "
            f"reasoning={str(with_reasoning).lower()}"
        )
        self.stdout.write(
            "followup contract: production orchestrator prompts/schema/tool catalog"
        )
        if options["show_payload"]:
            self._print_followup_payload(client, followup_request)

        try:
            followup_response = client.generate(followup_request)
        except LLMProviderRequestError as exc:
            self._print_provider_error("followup_call", exc)
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(
                    "Reproduced a post-tool follow-up failure. The provider_error block "
                    "is the evidence PT03 must address."
                )
            )
            return

        self.stdout.write(self.style.SUCCESS("followup_call: OK"))
        self.stdout.write(f"followup_text: {followup_response.normalized_text[:600]}")
        self.stdout.write("")
        self.stdout.write(
            "This exact variant was accepted. A green probe does not close PT03: run the "
            "real-provider scenario too, because product context and tool outputs can differ."
        )

    def _print_provider_error(self, stage: str, exc: LLMProviderRequestError) -> None:
        details = getattr(exc, "provider_error_details", None)
        self.stdout.write(self.style.ERROR(f"{stage}: provider request failed"))
        if isinstance(details, dict):
            self.stdout.write("provider_error:")
            self.stdout.write(json.dumps(details, ensure_ascii=False, indent=2))
        else:
            self.stdout.write(f"provider_error (unstructured): {exc}")

    def _print_followup_payload(self, client, request: LLMProviderRequest) -> None:
        model = str(getattr(client, "model", "") or "")
        payload = build_openai_responses_payload(request, model=model)
        self.stdout.write("followup_payload (exact production builder):")
        self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _apply_variant(
    request: LLMProviderRequest,
    *,
    strict: bool,
    with_tools: bool,
    with_reasoning: bool,
) -> LLMProviderRequest:
    metadata = dict(request.metadata or {})
    metadata["response_schema_strict"] = bool(strict)
    continuation_items = tuple(request.continuation_items or ())
    if not with_reasoning:
        metadata.pop("reasoning_effort", None)
        continuation_items = tuple(
            item
            for item in continuation_items
            if str(item.get("type") or "") != "reasoning"
        )
    return replace(
        request,
        metadata=metadata,
        tools=tuple(request.tools or ()) if with_tools else (),
        tool_choice=request.tool_choice if with_tools else None,
        parallel_tool_calls=request.parallel_tool_calls if with_tools else None,
        max_tool_calls=request.max_tool_calls if with_tools else None,
        continuation_items=continuation_items,
    )


def _probe_result_data(tool_name: str) -> dict:
    if tool_name == "update_proposal_preferences":
        return {
            "proposal_preferences": {
                "goal": "fat_loss",
                "meals_per_day": 4,
            },
            "nutrition_brief_patch": {
                "goal": "fat_loss",
                "meals_per_day": 4,
            },
        }
    return {"probe": "ok", "tool_name": tool_name}
