from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from django.contrib.auth.models import User
from django.test import override_settings
from django.utils import timezone

from ai_assistant.application.chat_engines import ChatEngineRequest
from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
from ai_assistant.application.orchestrator import AssistantOrchestratorConfig, ExternalLLMOrchestrator
from ai_assistant.application.tools import (
    TOOL_READ_USER_PROFILE_CONTEXT,
    TOOL_SHARE_PREFERENCE_DRAFT_CARD,
    TOOL_SHARE_PROFILE_DRAFT_CARD,
    TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
    TOOL_UPDATE_PREFERENCE_DRAFT,
    TOOL_UPDATE_PROFILE_DRAFT,
    TOOL_UPDATE_PROPOSAL_PREFERENCES,
)
from ai_assistant.infrastructure.providers.fake_client import FakeLLMClient
from notas.application.ai_intake.chat_engine import (
    AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
    LLMPreviewNutritionIntakeChatEngine,
)
from notas.application.ai_intake.nutrition_brief import (
    NutritionConversationState,
    serialize_conversation,
)
from notas.domain.models import (
    DailyPlan,
    Food,
    Meal,
    NutritionProposal,
    Plan,
    Profile,
    Program,
    WeightLog,
)


_FORBIDDEN_APPLY_TOOLS = {
    "apply_approved_proposal",
    "apply_proposal",
    "apply_validated_proposal",
}
_CARD_KIND_TO_UPDATE_TOOL = {
    "profile": TOOL_UPDATE_PROFILE_DRAFT,
    "preference": TOOL_UPDATE_PREFERENCE_DRAFT,
    "proposal_preferences": TOOL_UPDATE_PROPOSAL_PREFERENCES,
}
_CARD_KIND_TO_SHARE_TOOLS = {
    "profile": {TOOL_READ_USER_PROFILE_CONTEXT, TOOL_SHARE_PROFILE_DRAFT_CARD},
    "preference": {TOOL_SHARE_PREFERENCE_DRAFT_CARD},
    "proposal_preferences": {TOOL_SHARE_PROPOSAL_PREFERENCES_CARD},
}
_PREFERENCE_FIELD_TO_BRIEF_FIELDS = {
    "avoided_foods": {"excluded_foods"},
    "preferred_foods": {"preferred_foods"},
    "preferred_meals_per_day": {"meals_per_day"},
    "budget_preference": {"budget_level"},
    "simplicity_preference": {"style_preferences", "complexity_level"},
    "variety_preference": {"style_preferences", "complexity_level"},
}


def assistant_envelope(
    content: str,
    *,
    intent: str = "capture_nutrition_brief",
    confidence: float = 0.85,
    slots: Mapping[str, Any] | None = None,
    missing_slots: Sequence[str] | None = None,
    tool_requests: Sequence[Mapping[str, Any]] | None = None,
    requires_human_review: bool = False,
) -> str:
    """Build a provider-like structured response for replay scenarios."""

    return json.dumps(
        {
            "intent": {
                "name": intent,
                "confidence": confidence,
                "missing_slots": list(missing_slots or []),
                "slots": dict(slots or {}),
                "summary": content[:160],
                "safety_flags": [],
            },
            "assistant_message": {"content": content},
            "requires_human_review": bool(requires_human_review),
            "tool_requests": list(tool_requests or []),
        },
        ensure_ascii=False,
    )


def tool_request(tool_name: str, arguments: Mapping[str, Any], *, reason: str = "") -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "arguments": dict(arguments or {}),
        "reason": reason or f"Run {tool_name} during replay.",
    }


@dataclass(frozen=True)
class ConversationReplayScenario:
    key: str
    description: str
    user_messages: Sequence[str]
    provider_responses: Sequence[str]
    expected_brief: Mapping[str, Any] = field(default_factory=dict)
    forbidden_visible_fragments: Sequence[str] = field(default_factory=tuple)
    required_visible_fragments: Sequence[str] = field(default_factory=tuple)
    stable_brief_fields: Sequence[str] = field(default_factory=tuple)
    fields_not_reasked_after_capture: Sequence[str] = field(default_factory=tuple)
    expected_brief_transitions: Mapping[str, Sequence[Any]] = field(default_factory=dict)
    required_tool_names: Sequence[str] = field(default_factory=tuple)
    forbidden_tool_names: Sequence[str] = field(default_factory=tuple)
    expected_final_card_counts: Mapping[str, int] = field(default_factory=dict)
    expected_reviewable_proposal_delta: int = 0


@dataclass(frozen=True)
class ReplayProviderExchange:
    index: int
    assistant_message: str
    missing_slots: Sequence[str]
    tool_requests: Sequence[Mapping[str, Any]]

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(
            str(request.get("tool_name") or "")
            for request in self.tool_requests
            if isinstance(request, Mapping) and request.get("tool_name")
        )


@dataclass(frozen=True)
class ConversationReplayTurn:
    index: int
    user_message: str
    visible_message: str
    engine_name: str
    metadata: Mapping[str, Any]
    brief_snapshot: Mapping[str, Any]
    provider_exchanges: Sequence[ReplayProviderExchange] = field(default_factory=tuple)
    tool_names: Sequence[str] = field(default_factory=tuple)
    profile_card_count: int = 0
    preference_card_count: int = 0
    proposal_preferences_card_count: int = 0
    profile_card_delta: int = 0
    preference_card_delta: int = 0
    proposal_preferences_card_delta: int = 0

    def card_delta(self, kind: str) -> int:
        return {
            "profile": self.profile_card_delta,
            "preference": self.preference_card_delta,
            "proposal_preferences": self.proposal_preferences_card_delta,
        }[kind]


@dataclass(frozen=True)
class ReplayInvariantOutcome:
    key: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ConversationReplayResult:
    scenario: ConversationReplayScenario
    turns: Sequence[ConversationReplayTurn]
    final_state: NutritionConversationState
    fake_provider_requests_count: int
    initial_persistence_snapshot: Mapping[str, Any]
    final_persistence_snapshot: Mapping[str, Any]

    @property
    def final_brief(self):
        return self.final_state.result.brief

    @property
    def visible_messages(self) -> list[str]:
        return [turn.visible_message for turn in self.turns]

    @property
    def all_tool_names(self) -> tuple[str, ...]:
        return tuple(tool_name for turn in self.turns for tool_name in turn.tool_names)

    @property
    def final_card_counts(self) -> dict[str, int]:
        if not self.turns:
            return {"profile": 0, "preference": 0, "proposal_preferences": 0}
        final_turn = self.turns[-1]
        return {
            "profile": final_turn.profile_card_count,
            "preference": final_turn.preference_card_count,
            "proposal_preferences": final_turn.proposal_preferences_card_count,
        }

    def invariant_outcomes(self) -> list[ReplayInvariantOutcome]:
        checks = (
            ("visible_boundary", self._assert_visible_boundary),
            ("expected_brief", self._assert_expected_brief),
            ("stable_captured_facts", self._assert_stable_captured_facts),
            ("known_facts_not_reasked", self._assert_known_facts_not_reasked),
            ("card_update_share_boundary", self._assert_card_update_share_boundary),
            ("tool_contract", self._assert_tool_contract),
            ("brief_transitions", self._assert_brief_transitions),
            ("approval_only_persistence", self._assert_approval_only_persistence),
        )
        outcomes: list[ReplayInvariantOutcome] = []
        for key, check in checks:
            try:
                detail = check()
            except AssertionError as exc:
                outcomes.append(ReplayInvariantOutcome(key=key, passed=False, detail=str(exc)))
            else:
                outcomes.append(ReplayInvariantOutcome(key=key, passed=True, detail=detail))
        return outcomes

    def assert_invariants(self) -> None:
        failures = [outcome for outcome in self.invariant_outcomes() if not outcome.passed]
        if failures:
            details = "; ".join(f"{failure.key}: {failure.detail}" for failure in failures)
            raise AssertionError(f"Replay invariant failure(s): {details}")

    def assert_clean(self) -> None:
        """Backward-compatible alias for the invariant suite."""

        self.assert_invariants()

    def _assert_visible_boundary(self) -> str:
        visible_blob = "\n".join(self.visible_messages)
        forbidden = [
            "assistant_message",
            "tool_requests",
            "missing_slots",
            "requires_human_review",
            "NutritionBrief",
            "pending_field",
        ]
        forbidden.extend(self.scenario.forbidden_visible_fragments)
        for fragment in forbidden:
            if fragment and fragment in visible_blob:
                raise AssertionError(f"forbidden visible fragment leaked: {fragment!r}")
        for fragment in self.scenario.required_visible_fragments:
            if fragment and fragment not in visible_blob:
                raise AssertionError(f"required visible fragment was not shown: {fragment!r}")
        return "visible text contains no provider envelope or internal state markers"

    def _assert_expected_brief(self) -> str:
        for field_name, expected_value in dict(self.scenario.expected_brief or {}).items():
            actual_value = getattr(self.final_brief, field_name)
            if actual_value != expected_value:
                raise AssertionError(
                    f"expected final brief {field_name}={expected_value!r}, got {actual_value!r}"
                )
        return f"{len(self.scenario.expected_brief)} final brief field(s) matched"

    def _assert_stable_captured_facts(self) -> str:
        checked = 0
        for field_name in self.scenario.stable_brief_fields:
            captured = False
            captured_value = None
            for turn in self.turns:
                value = turn.brief_snapshot.get(field_name)
                if not captured and not _is_empty_replay_value(value):
                    captured = True
                    captured_value = value
                    continue
                if captured and value != captured_value:
                    raise AssertionError(
                        f"captured fact {field_name} changed from {captured_value!r} to {value!r} "
                        f"on turn {turn.index}"
                    )
            if not captured:
                raise AssertionError(f"stable fact {field_name} was never captured")
            checked += 1
        return f"{checked} captured fact(s) survived later turns"

    def _assert_known_facts_not_reasked(self) -> str:
        watched = set(self.scenario.fields_not_reasked_after_capture)
        known: set[str] = set()
        for turn in self.turns:
            for exchange in turn.provider_exchanges:
                repeated = known.intersection(exchange.missing_slots).intersection(watched)
                if repeated:
                    raise AssertionError(
                        f"known field(s) marked missing again in provider exchange {exchange.index}: "
                        f"{sorted(repeated)}"
                    )
                for request in exchange.tool_requests:
                    known.update(_captured_brief_fields_from_tool_request(request))
            for field_name in watched:
                if not _is_empty_replay_value(turn.brief_snapshot.get(field_name)):
                    known.add(field_name)
        return f"{len(watched)} watched field(s) were not reintroduced as missing"

    def _assert_card_update_share_boundary(self) -> str:
        for turn in self.turns:
            tool_names = set(turn.tool_names)
            for kind, update_tool in _CARD_KIND_TO_UPDATE_TOOL.items():
                share_tools = _CARD_KIND_TO_SHARE_TOOLS[kind]
                delta = turn.card_delta(kind)
                if update_tool in tool_names and not tool_names.intersection(share_tools) and delta:
                    raise AssertionError(
                        f"{update_tool} rendered {kind} card(s) without an explicit share tool on turn {turn.index}"
                    )
                if tool_names.intersection(share_tools) and delta < 1:
                    raise AssertionError(
                        f"explicit {kind} share tool did not render a card on turn {turn.index}"
                    )
        for kind, expected_count in self.scenario.expected_final_card_counts.items():
            actual_count = self.final_card_counts.get(kind, 0)
            if actual_count != expected_count:
                raise AssertionError(
                    f"expected {expected_count} final {kind} card(s), got {actual_count}"
                )
        return "draft updates stayed silent and explicit share tools controlled card rendering"

    def _assert_tool_contract(self) -> str:
        actual = set(self.all_tool_names)
        required = set(self.scenario.required_tool_names)
        missing = required.difference(actual)
        if missing:
            raise AssertionError(f"required tool(s) were not requested: {sorted(missing)}")
        forbidden = _FORBIDDEN_APPLY_TOOLS.union(self.scenario.forbidden_tool_names)
        used_forbidden = actual.intersection(forbidden)
        if used_forbidden:
            raise AssertionError(f"forbidden apply tool(s) were requested: {sorted(used_forbidden)}")
        return f"{len(actual)} distinct tool(s) respected the scenario contract"

    def _assert_brief_transitions(self) -> str:
        checked = 0
        for field_name, expected_sequence in self.scenario.expected_brief_transitions.items():
            actual_sequence = _compressed_non_empty_values(
                turn.brief_snapshot.get(field_name) for turn in self.turns
            )
            if not _is_subsequence(list(expected_sequence), actual_sequence):
                raise AssertionError(
                    f"expected transition for {field_name} to include {list(expected_sequence)!r}, "
                    f"got {actual_sequence!r}"
                )
            checked += 1
        return f"{checked} intentional brief transition(s) matched"

    def _assert_approval_only_persistence(self) -> str:
        before = self.initial_persistence_snapshot
        after = self.final_persistence_snapshot
        for key in ("profile", "weight_logs", "final_entity_counts", "applied_proposal_ids"):
            if before.get(key) != after.get(key):
                raise AssertionError(f"persistent boundary changed for {key}: {before.get(key)!r} -> {after.get(key)!r}")
        proposal_delta = int(after.get("reviewable_proposal_count", 0)) - int(
            before.get("reviewable_proposal_count", 0)
        )
        if proposal_delta != self.scenario.expected_reviewable_proposal_delta:
            raise AssertionError(
                f"expected reviewable proposal delta {self.scenario.expected_reviewable_proposal_delta}, "
                f"got {proposal_delta}"
            )
        return "draft facts did not mutate profile/final objects; only configured reviewable proposals were created"


def built_in_replay_scenarios() -> dict[str, ConversationReplayScenario]:
    return {
        "dieta_con_ficha_tool_led": _diet_with_profile_tool_led_scenario(),
        "datos_agrupados_orden_libre": _grouped_facts_free_order_scenario(),
        "cambio_direccion": _change_direction_scenario(),
        "json_visible_boundary": _json_visible_boundary_scenario(),
    }


def get_replay_scenario(key: str) -> ConversationReplayScenario:
    scenarios = built_in_replay_scenarios()
    try:
        return scenarios[key]
    except KeyError as exc:
        raise ValueError(f"Unknown replay scenario: {key}") from exc


def run_replay_scenario(
    scenario: ConversationReplayScenario,
    *,
    user: User | None = None,
    assert_clean: bool = True,
) -> ConversationReplayResult:
    user = user or ensure_replay_user()
    fake_client = FakeLLMClient(responses=scenario.provider_responses, model="fake-replay-llm")
    orchestrator = ExternalLLMOrchestrator(
        llm_client=fake_client,
        config=AssistantOrchestratorConfig(
            max_tool_loop_iterations=3,
            max_tool_requests_per_turn=4,
            enable_reviewable_proposal_tools=True,
            max_input_tokens=20000,
            max_context_chars=30000,
            max_message_chars=6000,
            max_output_tokens=1200,
        ),
    )
    engine = LLMPreviewNutritionIntakeChatEngine(
        llm_engine=ExternalLLMChatEngine(orchestrator=orchestrator)
    )

    initial_persistence_snapshot = _persistence_snapshot(user)
    state_payload: dict[str, Any] | None = None
    turns: list[ConversationReplayTurn] = []
    previous_card_counts = {"profile": 0, "preference": 0, "proposal_preferences": 0}
    exchange_index = 0
    with override_settings(AI_ASSISTANT_CREDITS_ENABLED=False):
        for index, message in enumerate(scenario.user_messages, start=1):
            response_offset = len(fake_client.generated_responses)
            result = engine.continue_chat(
                ChatEngineRequest(
                    message=message,
                    existing_payload=state_payload,
                    user_id=user.id,
                    metadata={
                        "tool_user": user,
                        "debug_ai_assistant": True,
                        "chat_engine_mode": AI_ASSISTANT_CHAT_ENGINE_LLM_PREVIEW,
                        "conversation_id": f"replay-{scenario.key}",
                        "turn_id": f"replay-{scenario.key}-{index}",
                    },
                )
            )
            state_payload = serialize_conversation(result.state)
            exchanges: list[ReplayProviderExchange] = []
            for generated_response in fake_client.generated_responses[response_offset:]:
                exchange_index += 1
                exchanges.append(_provider_exchange(exchange_index, generated_response.text))
            tool_names = tuple(tool_name for exchange in exchanges for tool_name in exchange.tool_names)
            card_counts = {
                "profile": len([m for m in result.state.messages if m.profile_draft_card]),
                "preference": len([m for m in result.state.messages if m.preference_draft_card]),
                "proposal_preferences": len([m for m in result.state.messages if m.proposal_preferences_card]),
            }
            turns.append(
                ConversationReplayTurn(
                    index=index,
                    user_message=message,
                    visible_message=result.assistant_text,
                    engine_name=result.engine_name,
                    metadata=dict(result.metadata or {}),
                    brief_snapshot=_brief_snapshot(result.state),
                    provider_exchanges=tuple(exchanges),
                    tool_names=tool_names,
                    profile_card_count=card_counts["profile"],
                    preference_card_count=card_counts["preference"],
                    proposal_preferences_card_count=card_counts["proposal_preferences"],
                    profile_card_delta=card_counts["profile"] - previous_card_counts["profile"],
                    preference_card_delta=card_counts["preference"] - previous_card_counts["preference"],
                    proposal_preferences_card_delta=(
                        card_counts["proposal_preferences"]
                        - previous_card_counts["proposal_preferences"]
                    ),
                )
            )
            previous_card_counts = card_counts

    replay_result = ConversationReplayResult(
        scenario=scenario,
        turns=turns,
        final_state=result.state,
        fake_provider_requests_count=len(fake_client.requests),
        initial_persistence_snapshot=initial_persistence_snapshot,
        final_persistence_snapshot=_persistence_snapshot(user),
    )
    if assert_clean:
        replay_result.assert_invariants()
    return replay_result


def ensure_replay_user(username: str = "ai_replay_user") -> User:
    user, _created = User.objects.get_or_create(
        username=username,
        defaults={"email": f"{username}@example.com"},
    )
    plan, _ = Plan.objects.get_or_create(
        name="Replay Plan",
        role="member",
        defaults={
            "can_create_meal": True,
            "can_create_dailyplan": True,
            "can_create_program": True,
        },
    )
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={"role": "member", "plan": plan, "height_cm": 188},
    )
    profile.role = profile.role or "member"
    profile.plan = profile.plan or plan
    profile.height_cm = profile.height_cm or 188
    profile.sex = ""
    profile.birth_date = None
    profile.save(update_fields=["role", "plan", "height_cm", "sex", "birth_date"])
    WeightLog.objects.update_or_create(
        user=user,
        date=timezone.localdate(),
        defaults={"weight_kg": 84, "source": WeightLog.SOURCE_MANUAL},
    )
    return User.objects.get(pk=user.pk)


def _brief_snapshot(state: NutritionConversationState) -> dict[str, Any]:
    brief = state.result.brief
    return {
        "goal": brief.goal,
        "requested_entity": brief.requested_entity,
        "subject_source": brief.subject_source,
        "weight_kg": brief.weight_kg,
        "height_cm": brief.height_cm,
        "age_years": brief.age_years,
        "sex": brief.sex,
        "activity_level": brief.activity_level,
        "training_frequency": brief.training_frequency,
        "meals_per_day": brief.meals_per_day,
        "style_preferences": list(brief.style_preferences or []),
        "excluded_foods": list(brief.excluded_foods or []),
        "preferred_foods": list(brief.preferred_foods or []),
        "complexity_level": brief.complexity_level,
        "budget_level": brief.budget_level,
        "field_sources": dict(brief.field_sources or {}),
    }


def _provider_exchange(index: int, response_text: str) -> ReplayProviderExchange:
    try:
        payload = json.loads(response_text)
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    intent = payload.get("intent") if isinstance(payload.get("intent"), dict) else {}
    assistant_message = payload.get("assistant_message")
    if isinstance(assistant_message, dict):
        assistant_message = assistant_message.get("content")
    return ReplayProviderExchange(
        index=index,
        assistant_message=str(assistant_message or ""),
        missing_slots=tuple(str(value) for value in list(intent.get("missing_slots") or [])),
        tool_requests=tuple(
            dict(request) for request in list(payload.get("tool_requests") or []) if isinstance(request, dict)
        ),
    )


def _captured_brief_fields_from_tool_request(request: Mapping[str, Any]) -> set[str]:
    tool_name = str(request.get("tool_name") or "")
    arguments = request.get("arguments") if isinstance(request.get("arguments"), Mapping) else {}
    updates = arguments.get("updates") if isinstance(arguments.get("updates"), Mapping) else {}
    if tool_name in {TOOL_UPDATE_PROFILE_DRAFT, TOOL_UPDATE_PROPOSAL_PREFERENCES}:
        return set(updates)
    if tool_name == TOOL_UPDATE_PREFERENCE_DRAFT:
        captured: set[str] = set()
        for field_name in updates:
            captured.update(_PREFERENCE_FIELD_TO_BRIEF_FIELDS.get(field_name, {field_name}))
        return captured
    return set()


def _persistence_snapshot(user: User) -> dict[str, Any]:
    profile = Profile.objects.get(user=user)
    weight_logs = list(
        WeightLog.objects.filter(user=user)
        .order_by("date", "id")
        .values_list("date", "weight_kg", "source")
    )
    return {
        "profile": {
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
            "sex": profile.sex,
            "height_cm": profile.height_cm,
            "onboarding_completed_at": (
                profile.onboarding_completed_at.isoformat() if profile.onboarding_completed_at else None
            ),
            "onboarding_version": profile.onboarding_version,
        },
        "weight_logs": [
            (date.isoformat(), float(weight_kg), source)
            for date, weight_kg, source in weight_logs
        ],
        "final_entity_counts": {
            "foods": Food.objects.filter(created_by=user).count(),
            "meals": Meal.objects.filter(created_by=user).count(),
            "dailyplans": DailyPlan.objects.filter(created_by=user).count(),
            "programs": Program.objects.filter(created_by=user).count(),
        },
        "reviewable_proposal_count": NutritionProposal.objects.filter(
            created_by=user,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        ).count(),
        "applied_proposal_ids": tuple(
            NutritionProposal.objects.filter(
                created_by=user,
                status=NutritionProposal.STATUS_APPLIED,
            ).values_list("id", flat=True)
        ),
    }


def _compressed_non_empty_values(values) -> list[Any]:
    compressed: list[Any] = []
    for value in values:
        if _is_empty_replay_value(value):
            continue
        if not compressed or value != compressed[-1]:
            compressed.append(value)
    return compressed


def _is_subsequence(expected: list[Any], actual: list[Any]) -> bool:
    if not expected:
        return True
    position = 0
    for value in actual:
        if value == expected[position]:
            position += 1
            if position == len(expected):
                return True
    return False


def _is_empty_replay_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _diet_with_profile_tool_led_scenario() -> ConversationReplayScenario:
    return ConversationReplayScenario(
        key="dieta_con_ficha_tool_led",
        description="LLM-led proposal intake using ficha, profile draft tools and proposal preferences.",
        user_messages=(
            "Hola buen día!",
            "Quiero una dieta",
            "Quiero aumentar de muscilo",
            "usemos mi ficha personal",
            "Completemoslos",
            "38 años",
            "hombre",
            "Entreno 3 veces por semana, intensidad alta",
            "3 comidas al día",
            "Algo simple",
        ),
        provider_responses=(
            assistant_envelope(
                "¡Hola! Buen día. ¿En qué te puedo ayudar hoy con My Scoope?",
                intent="small_talk",
            ),
            assistant_envelope(
                "Perfecto, te ayudo a armarla. Primero definamos el objetivo del plan.",
                slots={"requested_entity": "daily_plan"},
                missing_slots=["goal"],
                tool_requests=(
                    tool_request(
                        "update_proposal_preferences",
                        {"updates": {"requested_entity": "daily_plan"}},
                        reason="Registrar que el usuario pidió una dieta/plan diario.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto, te ayudo a armarla. ¿Cuál es tu objetivo principal para este plan?",
                missing_slots=["goal"],
            ),
            assistant_envelope(
                "Perfecto, lo orientaremos a ganar masa muscular.",
                slots={"goal": "muscle_gain"},
                tool_requests=(
                    tool_request(
                        "update_proposal_preferences",
                        {"updates": {"goal": "muscle_gain"}},
                        reason="Registrar el objetivo interpretado por el LLM.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto. ¿Quieres que use tu ficha personal como base o prefieres entregar datos nuevos?",
                missing_slots=["subject_source"],
            ),
            assistant_envelope(
                "Ya tengo tu ficha como base. Es mejor completar los datos pendientes para afinar el cálculo; también podemos continuar con una versión inicial si prefieres.",
                tool_requests=(
                    tool_request(
                        "read_user_profile_context",
                        {},
                        reason="Leer la ficha personal solicitada por el usuario.",
                    ),
                ),
            ),
            assistant_envelope(
                "Te dejo visible la ficha que usaremos. Si quieres, completemos edad, sexo y actividad para afinar la propuesta.",
                missing_slots=["age_years", "sex", "activity_level"],
            ),
            assistant_envelope(
                "Vamos paso a paso. Cuéntame tu edad.",
                missing_slots=["age_years", "sex", "activity_level"],
            ),
            assistant_envelope(
                "Gracias, ya registré la edad. Ahora cuéntame qué sexo debo usar para el cálculo.",
                tool_requests=(
                    tool_request(
                        "update_profile_draft",
                        {"updates": {"age_years": 38}},
                        reason="Registrar edad entregada por el usuario.",
                    ),
                ),
            ),
            assistant_envelope(
                "Gracias, ya registré la edad. Ahora cuéntame qué sexo debo usar para el cálculo.",
                missing_slots=["sex", "activity_level"],
            ),
            assistant_envelope(
                "Perfecto, registro hombre para el cálculo. Ahora cuéntame cómo es tu actividad o entrenamiento durante una semana normal.",
                tool_requests=(
                    tool_request(
                        "update_profile_draft",
                        {"updates": {"sex": "male"}},
                        reason="Registrar sexo usado para cálculo.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto, registro hombre para el cálculo. Ahora cuéntame cómo es tu actividad o entrenamiento durante una semana normal.",
                missing_slots=["activity_level"],
            ),
            assistant_envelope(
                "Bien, registro 3 entrenamientos por semana y actividad alta. Para esta propuesta, ¿cuántas comidas al día te acomodan?",
                tool_requests=(
                    tool_request(
                        "update_profile_draft",
                        {"updates": {"training_frequency": 3, "activity_level": "high"}},
                        reason="Registrar entrenamiento semanal y actividad interpretados por el LLM.",
                    ),
                    tool_request(
                        "share_profile_draft_card",
                        {
                            "profile_draft": {
                                "weight_kg": 84,
                                "height_cm": 188,
                                "age_years": 38,
                                "sex": "male",
                                "activity_level": "high",
                                "training_frequency": 3,
                                "field_sources": {
                                    "weight_kg": "profile",
                                    "height_cm": "profile",
                                    "age_years": "chat_draft",
                                    "sex": "chat_draft",
                                    "activity_level": "chat_draft",
                                    "training_frequency": "chat_draft",
                                },
                            }
                        },
                        reason="Mostrar la ficha una vez completado el grupo de datos pendientes.",
                    ),
                ),
            ),
            assistant_envelope(
                "Bien, registro 3 entrenamientos por semana y actividad alta. Para esta propuesta, ¿cuántas comidas al día te acomodan?",
                missing_slots=["meals_per_day"],
            ),
            assistant_envelope(
                "Perfecto, usaré 3 comidas al día para esta propuesta. ¿Prefieres que el plan sea simple, variado, económico o con poca preparación?",
                tool_requests=(
                    tool_request(
                        "update_proposal_preferences",
                        {"updates": {"meals_per_day": 3}},
                        reason="Registrar comidas por día para esta propuesta.",
                    ),
                    tool_request(
                        "share_proposal_preferences_card",
                        {
                            "proposal_preferences": {
                                "goal": "muscle_gain",
                                "requested_entity": "daily_plan",
                                "meals_per_day": 3,
                                "field_sources": {
                                    "goal": "chat_draft",
                                    "requested_entity": "chat_draft",
                                    "meals_per_day": "chat_draft",
                                },
                            }
                        },
                        reason="Mostrar la dirección de la propuesta una vez definidos sus parámetros principales.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto, usaré 3 comidas al día para esta propuesta. ¿Prefieres que el plan sea simple, variado, económico o con poca preparación?",
                missing_slots=["style_preferences"],
            ),
            assistant_envelope(
                "Perfecto, lo dejé simple. Con esto ya tengo una base consistente para avanzar a una propuesta revisable.",
                tool_requests=(
                    tool_request(
                        "update_preference_draft",
                        {"updates": {"simplicity_preference": "high"}},
                        reason="Registrar preferencia de simplicidad.",
                    ),
                    tool_request(
                        "share_preference_draft_card",
                        {
                            "preference_draft": {
                                "simplicity_preference": "high",
                                "field_sources": {"simplicity_preference": "chat_draft"},
                            }
                        },
                        reason="Mostrar las preferencias cuando ya existe una decisión útil para revisar.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto, lo dejé simple. Con esto ya tengo una base consistente para avanzar a una propuesta revisable.",
            ),
        ),
        expected_brief={
            "goal": "muscle_gain",
            "requested_entity": "daily_plan",
            "subject_source": "self_profile",
            "weight_kg": 84,
            "height_cm": 188,
            "age_years": 38,
            "sex": "male",
            "activity_level": "high",
            "training_frequency": 3,
            "meals_per_day": 3,
        },
        forbidden_visible_fragments=("¿Cuál es tu objetivo principal ahora", "draft", "slots"),
        required_visible_fragments=("ficha", "propuesta"),
        stable_brief_fields=(
            "goal",
            "requested_entity",
            "subject_source",
            "weight_kg",
            "height_cm",
            "age_years",
            "sex",
            "activity_level",
            "training_frequency",
            "meals_per_day",
        ),
        fields_not_reasked_after_capture=(
            "goal",
            "requested_entity",
            "subject_source",
            "age_years",
            "sex",
            "activity_level",
            "training_frequency",
            "meals_per_day",
        ),
        required_tool_names=(
            TOOL_UPDATE_PROPOSAL_PREFERENCES,
            TOOL_READ_USER_PROFILE_CONTEXT,
            TOOL_UPDATE_PROFILE_DRAFT,
            TOOL_SHARE_PROFILE_DRAFT_CARD,
            TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
            TOOL_UPDATE_PREFERENCE_DRAFT,
            TOOL_SHARE_PREFERENCE_DRAFT_CARD,
        ),
        expected_final_card_counts={
            "profile": 2,
            "preference": 1,
            "proposal_preferences": 1,
        },
    )


def _grouped_facts_free_order_scenario() -> ConversationReplayScenario:
    profile_draft = {
        "weight_kg": 85,
        "height_cm": 188,
        "age_years": 38,
        "sex": "male",
        "activity_level": "high",
        "training_frequency": 3,
        "field_sources": {
            "weight_kg": "chat_draft",
            "height_cm": "chat_draft",
            "age_years": "chat_draft",
            "sex": "chat_draft",
            "activity_level": "chat_draft",
            "training_frequency": "chat_draft",
        },
    }
    proposal_preferences = {
        "goal": "muscle_gain",
        "requested_entity": "daily_plan",
        "meals_per_day": 4,
        "field_sources": {
            "goal": "chat_draft",
            "requested_entity": "chat_draft",
            "meals_per_day": "chat_draft",
        },
    }
    preference_draft = {
        "simplicity_preference": "high",
        "field_sources": {"simplicity_preference": "chat_draft"},
    }
    return ConversationReplayScenario(
        key="datos_agrupados_orden_libre",
        description=(
            "Several profile and proposal facts arrive together, are captured in one tool-led turn, "
            "and remain silent until the user asks to review the cards."
        ),
        user_messages=(
            "Quiero una dieta para ganar músculo. Tengo 38 años, soy hombre, peso 85 kg, mido 188 cm, entreno 3 veces con intensidad alta, prefiero 4 comidas y algo simple.",
            "Muéstrame la ficha y las preferencias que usarás.",
        ),
        provider_responses=(
            assistant_envelope(
                "Perfecto. Registré todos esos datos juntos y ya tengo una base consistente para trabajar.",
                tool_requests=(
                    tool_request(
                        TOOL_UPDATE_PROFILE_DRAFT,
                        {"updates": {key: value for key, value in profile_draft.items() if key != "field_sources"}},
                        reason="Registrar los datos físicos y de actividad entregados en un solo mensaje.",
                    ),
                    tool_request(
                        TOOL_UPDATE_PROPOSAL_PREFERENCES,
                        {"updates": {key: value for key, value in proposal_preferences.items() if key != "field_sources"}},
                        reason="Registrar objetivo, tipo de propuesta y comidas por día.",
                    ),
                    tool_request(
                        TOOL_UPDATE_PREFERENCE_DRAFT,
                        {"updates": {"simplicity_preference": "high"}},
                        reason="Registrar preferencia de simplicidad.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto. Registré todos esos datos juntos y ya tengo una base consistente para trabajar."
            ),
            assistant_envelope(
                "Claro. Te muestro los tres objetos que usaré como base para la propuesta.",
                tool_requests=(
                    tool_request(
                        TOOL_SHARE_PROFILE_DRAFT_CARD,
                        {"profile_draft": profile_draft},
                        reason="El usuario pidió revisar su ficha temporal.",
                    ),
                    tool_request(
                        TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
                        {"proposal_preferences": proposal_preferences},
                        reason="El usuario pidió revisar la dirección de la propuesta.",
                    ),
                    tool_request(
                        TOOL_SHARE_PREFERENCE_DRAFT_CARD,
                        {"preference_draft": preference_draft},
                        reason="El usuario pidió revisar sus preferencias.",
                    ),
                ),
            ),
            assistant_envelope(
                "Claro. Te muestro los tres objetos que usaré como base para la propuesta."
            ),
        ),
        expected_brief={
            "goal": "muscle_gain",
            "requested_entity": "daily_plan",
            "weight_kg": 85,
            "height_cm": 188,
            "age_years": 38,
            "sex": "male",
            "activity_level": "high",
            "training_frequency": 3,
            "meals_per_day": 4,
            "complexity_level": "low",
        },
        stable_brief_fields=(
            "goal",
            "requested_entity",
            "weight_kg",
            "height_cm",
            "age_years",
            "sex",
            "activity_level",
            "training_frequency",
            "meals_per_day",
            "complexity_level",
        ),
        fields_not_reasked_after_capture=(
            "goal",
            "requested_entity",
            "weight_kg",
            "height_cm",
            "age_years",
            "sex",
            "activity_level",
            "training_frequency",
            "meals_per_day",
        ),
        required_tool_names=(
            TOOL_UPDATE_PROFILE_DRAFT,
            TOOL_UPDATE_PROPOSAL_PREFERENCES,
            TOOL_UPDATE_PREFERENCE_DRAFT,
            TOOL_SHARE_PROFILE_DRAFT_CARD,
            TOOL_SHARE_PROPOSAL_PREFERENCES_CARD,
            TOOL_SHARE_PREFERENCE_DRAFT_CARD,
        ),
        expected_final_card_counts={
            "profile": 1,
            "preference": 1,
            "proposal_preferences": 1,
        },
        required_visible_fragments=("Registré todos esos datos", "tres objetos"),
    )


def _change_direction_scenario() -> ConversationReplayScenario:
    return ConversationReplayScenario(
        key="cambio_direccion",
        description=(
            "The user changes both requested entity and goal; the replay validates intentional transitions "
            "instead of treating the first interpretation as a fixed questionnaire state."
        ),
        user_messages=(
            "Quiero un plan diario para ganar masa muscular.",
            "Mejor hagamos un programa semanal para bajar grasa.",
            "Déjalo en 3 comidas al día y avancemos sin más preferencias por ahora.",
        ),
        provider_responses=(
            assistant_envelope(
                "Perfecto, tomo como punto de partida un plan diario para ganar masa muscular.",
                tool_requests=(
                    tool_request(
                        TOOL_UPDATE_PROPOSAL_PREFERENCES,
                        {"updates": {"requested_entity": "daily_plan", "goal": "muscle_gain"}},
                        reason="Registrar la primera dirección solicitada.",
                    ),
                ),
            ),
            assistant_envelope(
                "Perfecto, tomo como punto de partida un plan diario para ganar masa muscular."
            ),
            assistant_envelope(
                "Entendido. Cambio la dirección a un programa semanal orientado a bajar grasa.",
                tool_requests=(
                    tool_request(
                        TOOL_UPDATE_PROPOSAL_PREFERENCES,
                        {"updates": {"requested_entity": "program", "goal": "fat_loss"}},
                        reason="Aplicar el cambio explícito de dirección del usuario.",
                    ),
                ),
            ),
            assistant_envelope(
                "Entendido. Cambio la dirección a un programa semanal orientado a bajar grasa."
            ),
            assistant_envelope(
                "Listo: 3 comidas al día. Podemos avanzar sin forzar preferencias opcionales.",
                tool_requests=(
                    tool_request(
                        TOOL_UPDATE_PROPOSAL_PREFERENCES,
                        {"updates": {"meals_per_day": 3}},
                        reason="Registrar la cantidad de comidas elegida.",
                    ),
                ),
            ),
            assistant_envelope(
                "Listo: 3 comidas al día. Podemos avanzar sin forzar preferencias opcionales."
            ),
        ),
        expected_brief={
            "goal": "fat_loss",
            "requested_entity": "program",
            "meals_per_day": 3,
        },
        stable_brief_fields=("meals_per_day",),
        fields_not_reasked_after_capture=("goal", "requested_entity", "meals_per_day"),
        expected_brief_transitions={
            "goal": ("muscle_gain", "fat_loss"),
            "requested_entity": ("daily_plan", "program"),
        },
        required_tool_names=(TOOL_UPDATE_PROPOSAL_PREFERENCES,),
        expected_final_card_counts={
            "profile": 0,
            "preference": 0,
            "proposal_preferences": 0,
        },
        required_visible_fragments=("Cambio la dirección", "sin forzar preferencias opcionales"),
    )


def _json_visible_boundary_scenario() -> ConversationReplayScenario:
    raw_json_content = assistant_envelope(
        "Puedo ayudarte con una propuesta inicial. ¿Qué objetivo quieres para el plan?",
        slots={"requested_entity": "daily_plan"},
        missing_slots=["goal"],
        tool_requests=(
            tool_request(
                "update_proposal_preferences",
                {"updates": {"requested_entity": "daily_plan"}},
                reason="Registrar solicitud de dieta.",
            ),
        ),
    )
    return ConversationReplayScenario(
        key="json_visible_boundary",
        description="Structured provider envelopes must never be persisted as raw visible chat text.",
        user_messages=("Quiero una dieta",),
        provider_responses=(
            raw_json_content,
            assistant_envelope("Puedo ayudarte con una propuesta inicial. ¿Qué objetivo quieres para el plan?"),
        ),
        expected_brief={"requested_entity": "daily_plan"},
        forbidden_visible_fragments=("assistant_message", "tool_requests", "missing_slots"),
        required_visible_fragments=("objetivo",),
        stable_brief_fields=("requested_entity",),
        fields_not_reasked_after_capture=("requested_entity",),
        required_tool_names=(TOOL_UPDATE_PROPOSAL_PREFERENCES,),
        expected_final_card_counts={
            "profile": 0,
            "preference": 0,
            "proposal_preferences": 0,
        },
    )
