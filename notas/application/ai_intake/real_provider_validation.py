from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Any, Iterable, Mapping, Sequence

from django.conf import settings
from django.contrib.auth import get_user_model

from ai_assistant.application.chat_engines import ChatEngine, ChatEngineRequest
from ai_assistant.application.llm_chat_engine import ExternalLLMChatEngine
from ai_assistant.application.orchestrator import AssistantOrchestratorConfig, ExternalLLMOrchestrator
from ai_assistant.models import AICreditLedger, AIUsageEvent, AIUserCreditQuota
from notas.application.ai_intake.chat_engine import LLMNutritionIntakeChatEngine
from notas.application.ai_intake.nutrition_brief import (
    NutritionConversationState,
    serialize_conversation,
)
from notas.application.queries.user_nutrition_profile import get_user_nutrition_profile

OUTCOME_FIRST_ACTION_TYPE = "assistant.ai_nutrition_intake.outcome_first_validation"
OUTCOME_FIRST_VALIDATION_VERSION = "outcome_first.live_validation.v1"
POST_TOOL_LOCAL_ACK_FRAGMENTS = (
    "Los datos físicos quedaron actualizados para esta conversación.",
    "Las preferencias alimentarias quedaron actualizadas para esta propuesta.",
    "La dirección de la propuesta quedó actualizada.",
    "La información está disponible en la card para revisión.",
    "La propuesta quedó creada y disponible para revisión.",
    "La propuesta quedó actualizada y disponible para revisión.",
    "El resultado quedó listo para revisión.",
    "La información solicitada quedó disponible.",
    "El cambio autorizado quedó guardado.",
    "No encontré una propuesta disponible con ese identificador.",
    "No encontré esa información con los datos disponibles.",
    "No pude completar la operación con los datos disponibles.",
    "La información quedó actualizada para esta conversación.",
)

PROFILE_BEHAVIOR_FIELDS = (
    "weight_kg",
    "height_cm",
    "age_years",
    "sex",
)

PROFILE_DTO_FIELD_MAP = {
    "weight_kg": "current_weight_kg",
    "height_cm": "height_cm",
    "age_years": "age_years",
    "sex": "sex",
}

OUTCOME_FIRST_FORBIDDEN_VISIBLE_MARKERS = (
    "assistant_message",
    "tool_requests",
    "missing_slots",
    "requires_human_review",
    "nutritionbrief",
    "pending_field",
    "traceback",
)


@dataclass(frozen=True)
class RealProviderValidationScenario:
    key: str
    description: str
    user_messages: Sequence[str]
    expected_final_brief: Mapping[str, Any] = field(default_factory=dict)
    expected_brief_transitions: Mapping[str, Sequence[Any]] = field(default_factory=dict)
    stable_brief_fields: Sequence[str] = field(default_factory=tuple)
    fields_not_reasked_after_capture: Sequence[str] = field(default_factory=tuple)
    required_tool_names: Sequence[str] = field(default_factory=tuple)
    expected_tool_errors: Mapping[str, str] = field(default_factory=dict)
    min_final_card_counts: Mapping[str, int] = field(default_factory=dict)
    max_final_card_counts: Mapping[str, int] = field(default_factory=dict)
    manual_review_prompts: Sequence[str] = field(default_factory=tuple)
    forbidden_tool_names: Sequence[str] = field(default_factory=tuple)
    forbidden_visible_fragments: Sequence[str] = field(default_factory=tuple)
    max_repeated_opening_count: int | None = None
    max_tool_calls: int | None = None
    visible_reask_markers: Mapping[str, Sequence[str]] = field(default_factory=dict)
    profile_preflight_facts: Mapping[str, Any] = field(default_factory=dict)
    profile_preflight_missing_fields: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class RealProviderValidationTurn:
    index: int
    turn_id: str
    user_message: str
    assistant_message: str
    engine_name: str
    brief_snapshot: Mapping[str, Any]
    semantic_intent: str
    semantic_missing_slots: Sequence[str]
    tool_results: Sequence[Mapping[str, str]]
    card_counts: Mapping[str, int]
    card_deltas: Mapping[str, int]
    fallback: bool
    fallback_reason: str
    deterministic_runtime_invoked: bool
    provider: str
    model: str
    usage_observability: Mapping[str, Any]
    provider_parse_error: str = ""
    provider_contract_repair_attempted: bool = False
    provider_native_tool_transport: bool = False
    provider_native_tool_calls: int = 0
    provider_text_parse_ignored_due_to_native_tools: bool = False
    provider_incomplete_reasons: Sequence[str] = field(default_factory=tuple)
    provider_final_incomplete_reason: str = ""
    tool_followup_local_ack: bool = False
    tool_followup_local_ack_policy: str = ""
    provider_tool_followup_failed: bool = False
    provider_tool_followup_error_status: int | None = None
    provider_tool_followup_error_type: str = ""
    provider_tool_followup_error_code: str = ""
    provider_tool_followup_error_message: str = ""
    provider_tool_followup_error_param: str = ""
    provider_tool_followup_error_request_id: str = ""

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(
            str(item.get("tool_name") or "")
            for item in self.tool_results
            if str(item.get("tool_name") or "")
        )


@dataclass(frozen=True)
class RealProviderValidationCheck:
    key: str
    passed: bool
    detail: str
    severity: str = "hard"


@dataclass(frozen=True)
class RealProviderValidationScenarioResult:
    scenario: RealProviderValidationScenario
    conversation_id: str
    turns: Sequence[RealProviderValidationTurn]
    usage_events: Sequence[Mapping[str, Any]]
    checks: Sequence[RealProviderValidationCheck]

    @property
    def hard_failures(self) -> tuple[RealProviderValidationCheck, ...]:
        return tuple(check for check in self.checks if check.severity == "hard" and not check.passed)

    @property
    def passed(self) -> bool:
        return not self.hard_failures

    @property
    def final_brief(self) -> Mapping[str, Any]:
        return self.turns[-1].brief_snapshot if self.turns else {}

    @property
    def all_tool_names(self) -> tuple[str, ...]:
        return tuple(tool for turn in self.turns for tool in turn.tool_names)


@dataclass(frozen=True)
class RealProviderValidationReport:
    version: str
    run_id: str
    provider: str
    model: str
    user_id: int
    configured_chat_mode: str
    usage_observability_enabled: bool
    credits_enabled: bool
    scenarios: Sequence[RealProviderValidationScenarioResult]
    usage_summary: Mapping[str, Any]
    credit_summary: Mapping[str, Any]
    manual_review_prompts: Sequence[str]

    @property
    def hard_failures(self) -> tuple[RealProviderValidationCheck, ...]:
        return tuple(failure for scenario in self.scenarios for failure in scenario.hard_failures)

    @property
    def passed(self) -> bool:
        return not self.hard_failures

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "run_id": self.run_id,
            "status": "automated_checks_passed" if self.passed else "hard_regression",
            "provider": self.provider,
            "model": self.model,
            "user_id": self.user_id,
            "configured_chat_mode": self.configured_chat_mode,
            "validation_engine": "outcome_first_llm",
            "reviewable_proposal_tools_enabled": True,
            "usage_observability_enabled": self.usage_observability_enabled,
            "credits_enabled": self.credits_enabled,
            "usage_summary": dict(self.usage_summary),
            "credit_summary": dict(self.credit_summary),
            "manual_review_required": True,
            "ux_gate_status": "awaiting_manual_review" if self.passed else "blocked_by_hard_regression",
            "manual_review_prompts": list(self.manual_review_prompts),
            "scenarios": [_scenario_result_as_dict(item) for item in self.scenarios],
        }


def built_in_real_provider_scenarios() -> dict[str, RealProviderValidationScenario]:
    return {
        "saludo_y_descubrimiento": RealProviderValidationScenario(
            key="saludo_y_descubrimiento",
            description="Natural greeting and task discovery without a scripted questionnaire.",
            user_messages=("Hola. Necesito ayuda con mi alimentación.",),
            max_final_card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            manual_review_prompts=(
                "¿El saludo suena natural y reconoce la solicitud sin presentarse como formulario?",
                "¿La respuesta ayuda a descubrir la tarea sin enumerar una batería rígida de preguntas?",
            ),
        ),
        "tema_externo_breve": RealProviderValidationScenario(
            key="tema_externo_breve",
            description="Answer one off-domain question briefly without opening an unrelated workflow.",
            user_messages=("¿Qué opinas del mundial de fútbol?",),
            max_final_card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            max_tool_calls=0,
            forbidden_visible_fragments=(
                "read_user_profile_context",
                "update_profile_draft",
                "tool_requests",
                "mcp",
            ),
            manual_review_prompts=(
                "¿La respuesta es breve, amable y suficiente para una pregunta externa?",
                "¿Evita invitar a desarrollar una conversación extensa fuera de My Scoope?",
            ),
        ),
        "capacidades_en_lenguaje_de_producto": RealProviderValidationScenario(
            key="capacidades_en_lenguaje_de_producto",
            description="Explain My Scoope capabilities without exposing internal function or transport names.",
            user_messages=("¿Qué puedes hacer por mí dentro de My Scoope?",),
            max_final_card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            max_tool_calls=0,
            forbidden_visible_fragments=(
                "read_user_profile_context",
                "update_profile_draft",
                "update_proposal_preferences",
                "share_profile_draft_card",
                "create_validated_",
                "tool_requests",
                "mcp",
                "schema",
            ),
            manual_review_prompts=(
                "¿Las capacidades se explican como resultados útiles para el usuario?",
                "¿La respuesta evita nombres de functions, schemas, MCP e identificadores internos?",
            ),
        ),
        "referencia_ambigua_sin_tools": RealProviderValidationScenario(
            key="referencia_ambigua_sin_tools",
            description="Clarify an ambiguous situation before reading, writing or presenting cards.",
            user_messages=("¿Qué está pasando?",),
            max_final_card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            max_tool_calls=0,
            forbidden_visible_fragments=("tool_requests", "selection_reason", "missing_tool_selection_reason"),
            manual_review_prompts=(
                "¿La respuesta pide una aclaración breve en vez de adivinar el referente?",
                "¿Evita afirmar que leyó, cambió o encontró un objeto sin autorización clara?",
            ),
        ),
        "ficha_conocida_sin_repreguntas": RealProviderValidationScenario(
            key="ficha_conocida_sin_repreguntas",
            description=(
                "Read the personal ficha and continue without re-asking weight, height, age or sex "
                "when those facts are already available in the same tool-led turn."
            ),
            user_messages=(
                "Quiero una dieta para ganar masa muscular usando mi ficha personal.",
                "Dime solamente qué dato realmente falta para avanzar.",
            ),
            expected_final_brief={
                "goal": "muscle_gain",
                "requested_entity": "daily_plan",
                "subject_source": "self_profile",
            },
            stable_brief_fields=(
                "goal",
                "requested_entity",
                "subject_source",
            ),
            fields_not_reasked_after_capture=(
                "weight_kg",
                "height_cm",
                "age_years",
                "sex",
            ),
            visible_reask_markers={
                "weight_kg": ("cuánto pesas", "cuanto pesas", "tu peso", "peso actual"),
                "height_cm": ("cuánto mides", "cuanto mides", "tu altura", "altura actual"),
                "age_years": ("qué edad tienes", "que edad tienes", "tu edad", "edad actual"),
                "sex": ("qué sexo", "que sexo", "sexo debo usar", "tu sexo"),
            },
            required_tool_names=("read_user_profile_context", "update_proposal_preferences"),
            min_final_card_counts={"profile": 1},
            max_final_card_counts={"profile": 1, "preference": 0, "proposal_preferences": 0},
            max_repeated_opening_count=1,
            manual_review_prompts=(
                "¿El asistente usa cada dato realmente disponible en la ficha sin volver a pedirlo?",
                "¿La segunda respuesta menciona solo información que verdaderamente sigue pendiente?",
            ),
        ),
        "datos_agrupados_y_cards": RealProviderValidationScenario(
            key="datos_agrupados_y_cards",
            description=(
                "Capture many facts in one turn, preserve them on the next turn and share cards only "
                "after the user explicitly asks to review them."
            ),
            user_messages=(
                "Quiero una dieta para ganar músculo para mí. Usa mi ficha personal como base, pero para esta propuesta considera 38 años, hombre, 85 kg, 188 cm, fuerza 3 veces por semana con actividad alta, 4 comidas y algo simple.",
                "Antes de avanzar, muéstrame las preferencias de alimentación y de propuesta que usarás.",
            ),
            expected_final_brief={
                "goal": "muscle_gain",
                "requested_entity": "daily_plan",
                "subject_source": "self_profile",
                "weight_kg": 85.0,
                "height_cm": 188,
                "age_years": 38,
                "sex": "male",
                "activity_level": "high",
                "training_frequency": 3,
                "meals_per_day": 4,
                "complexity_level": "low",
                "is_ready_for_proposal": True,
            },
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
                "complexity_level",
            ),
            fields_not_reasked_after_capture=(
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
            required_tool_names=(
                "read_user_profile_context",
                "update_profile_draft",
                "update_proposal_preferences",
                "share_preference_draft_card",
                "share_proposal_preferences_card",
             ),
            min_final_card_counts={"profile": 1, "preference": 1, "proposal_preferences": 1},
            max_final_card_counts={"profile": 1, "preference": 1, "proposal_preferences": 1},
            max_repeated_opening_count=1,
            manual_review_prompts=(
                "¿La primera respuesta reconoce varios datos juntos sin repreguntarlos uno por uno?",
                "¿La card inicial de ficha aparece una sola vez al leerla y las otras cards solo cuando se solicitan?",
            ),
        ),
        "cambio_de_direccion": RealProviderValidationScenario(
            key="cambio_de_direccion",
            description="Accept an explicit change of goal and requested entity without defending the earlier path.",
            user_messages=(
                "Quiero un plan diario para ganar masa muscular.",
                "Mejor hagamos un programa semanal para bajar grasa.",
                "Déjalo en 3 comidas al día y avancemos sin más preferencias por ahora.",
            ),
            expected_final_brief={
                "goal": "fat_loss",
                "requested_entity": "program",
                "meals_per_day": 3,
            },
            expected_brief_transitions={
                "goal": ("muscle_gain", "fat_loss"),
                "requested_entity": ("daily_plan", "program"),
            },
            stable_brief_fields=("meals_per_day",),
            fields_not_reasked_after_capture=("goal", "requested_entity", "meals_per_day"),
            required_tool_names=("update_proposal_preferences",),
            max_final_card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            max_repeated_opening_count=1,
            manual_review_prompts=(
                "¿El asistente acepta el cambio inmediatamente, sin insistir en el objetivo anterior?",
                "¿Respeta que el usuario no quiere completar preferencias opcionales todavía?",
            ),
        ),
        "error_de_tool_y_recuperacion": RealProviderValidationScenario(
            key="error_de_tool_y_recuperacion",
            description="Exercise a safe read-tool not-found result and verify a human-readable recovery.",
            user_messages=(
                "Usa la herramienta read_proposal para revisar la propuesta 2147483647 y explícame qué encontraste.",
            ),
            required_tool_names=("read_proposal",),
            expected_tool_errors={"read_proposal": "error"},
            max_final_card_counts={"profile": 0, "preference": 0, "proposal_preferences": 0},
            manual_review_prompts=(
                "¿La respuesta explica de forma natural que la propuesta no está disponible?",
                "¿Evita mostrar códigos internos, trazas o lenguaje técnico innecesario?",
            ),
        ),
    }


def run_real_provider_validation(
    *,
    user: Any,
    scenario_keys: Sequence[str] | None = None,
    engine: ChatEngine | None = None,
    run_id: str | None = None,
) -> RealProviderValidationReport:
    if not getattr(user, "pk", None):
        raise ValueError("Outcome-first validation requires one persisted authenticated user.")

    provider = str(getattr(settings, "AI_ASSISTANT_LLM_PROVIDER", "") or "").strip().lower()
    if provider != "openai":
        raise ValueError("Live validation requires AI_ASSISTANT_LLM_PROVIDER=openai.")
    if not bool(getattr(settings, "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED", False)):
        raise ValueError(
            "Outcome-first live validation requires "
            "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED=true."
        )
    if not bool(
        getattr(settings, "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS", False)
    ):
        raise ValueError(
            "Live validation requires AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS=true."
        )

    selected_scenarios = tuple(
        _specialize_scenario_for_user(scenario, user=user)
        for scenario in _select_scenarios(scenario_keys)
    )
    validation_run_id = run_id or uuid.uuid4().hex
    validation_engine = engine or build_real_provider_validation_engine()
    usage_before = _usage_and_credit_snapshot(user=user, run_id=validation_run_id)

    scenario_results: list[RealProviderValidationScenarioResult] = []
    for scenario in selected_scenarios:
        scenario_results.append(
            _run_scenario(
                scenario=scenario,
                user=user,
                engine=validation_engine,
                run_id=validation_run_id,
            )
        )

    usage_after = _usage_and_credit_snapshot(user=user, run_id=validation_run_id)
    manual_prompts = tuple(
        dict.fromkeys(
            prompt
            for scenario in selected_scenarios
            for prompt in scenario.manual_review_prompts
        )
    )
    model = _first_non_empty(
        *(turn.model for result in scenario_results for turn in result.turns),
        str(getattr(settings, "AI_ASSISTANT_OPENAI_MODEL", "") or ""),
    )
    return RealProviderValidationReport(
        version=OUTCOME_FIRST_VALIDATION_VERSION,
        run_id=validation_run_id,
        provider=provider,
        model=model,
        user_id=int(user.pk),
        configured_chat_mode=str(getattr(settings, "AI_ASSISTANT_CHAT_ENGINE_MODE", "") or ""),
        usage_observability_enabled=True,
        credits_enabled=bool(getattr(settings, "AI_ASSISTANT_CREDITS_ENABLED", False)),
        scenarios=tuple(scenario_results),
        usage_summary=_usage_delta(usage_before, usage_after),
        credit_summary=_credit_delta(usage_before, usage_after),
        manual_review_prompts=manual_prompts,
    )


def _specialize_scenario_for_user(
    scenario: RealProviderValidationScenario,
    *,
    user: Any,
) -> RealProviderValidationScenario:
    """Bind profile-dependent assertions to the selected validation user.

    Live users may have incomplete onboarding data. The gate must require every
    fact that actually exists in the persisted ficha, while allowing the
    assistant to ask for fields that are genuinely absent. This also keeps a
    synchronization regression observable: any available profile fact is added
    to the expected final brief and stable-fact contract.
    """

    if scenario.key != "ficha_conocida_sin_repreguntas":
        return scenario

    profile = get_user_nutrition_profile(user).as_dict()
    available = {
        brief_field: profile.get(dto_field)
        for brief_field, dto_field in PROFILE_DTO_FIELD_MAP.items()
        if not _is_empty(profile.get(dto_field))
    }
    missing = tuple(
        field_name for field_name in PROFILE_BEHAVIOR_FIELDS if field_name not in available
    )
    expected_final_brief = dict(scenario.expected_final_brief)
    expected_final_brief.update(available)
    stable_brief_fields = tuple(
        dict.fromkeys((*scenario.stable_brief_fields, *available.keys()))
    )

    return replace(
        scenario,
        expected_final_brief=expected_final_brief,
        stable_brief_fields=stable_brief_fields,
        profile_preflight_facts=available,
        profile_preflight_missing_fields=missing,
    )


def _profile_preflight_check(
    scenario: RealProviderValidationScenario,
) -> RealProviderValidationCheck:
    available = dict(scenario.profile_preflight_facts)
    missing = tuple(scenario.profile_preflight_missing_fields)
    return RealProviderValidationCheck(
        key="profile_fixture",
        passed=True,
        detail=(
            f"persisted ficha available={list(available)}; "
            f"genuinely missing={list(missing)}"
        ),
        severity="diagnostic",
    )


def build_real_provider_validation_engine() -> LLMNutritionIntakeChatEngine:
    base_config = AssistantOrchestratorConfig.from_settings()
    config = replace(
        base_config,
        max_output_tokens=max(1400, int(base_config.max_output_tokens)),
        enable_reviewable_proposal_tools=True,
        max_tool_loop_iterations=max(
            4,
            int(getattr(settings, "AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS", 4) or 4),
        ),
        max_tool_requests_per_turn=max(
            4,
            int(getattr(settings, "AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN", 4) or 4),
        ),
    )
    orchestrator = ExternalLLMOrchestrator(config=config)
    return LLMNutritionIntakeChatEngine(
        llm_engine=ExternalLLMChatEngine(orchestrator=orchestrator)
    )


def get_validation_user(*, user_id: int | None = None, email: str = "") -> Any:
    User = get_user_model()
    if user_id:
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise ValueError(f"User id {user_id} does not exist.") from exc
    normalized_email = str(email or "").strip()
    if not normalized_email:
        raise ValueError("Provide --user-id or --user-email for outcome-first validation.")
    matches = User.objects.filter(email__iexact=normalized_email).order_by("pk")
    count = matches.count()
    if count != 1:
        raise ValueError(f"Expected exactly one user for that email; found {count}.")
    return matches.first()


def _run_scenario(
    *,
    scenario: RealProviderValidationScenario,
    user: Any,
    engine: ChatEngine,
    run_id: str,
) -> RealProviderValidationScenarioResult:
    conversation_id = f"outcome-{run_id[:20]}-{scenario.key}"[:80]
    existing_payload: Mapping[str, Any] | None = None
    turns: list[RealProviderValidationTurn] = []
    previous_cards = {"profile": 0, "preference": 0, "proposal_preferences": 0}

    for index, message in enumerate(scenario.user_messages, start=1):
        turn_id = f"{conversation_id}-{index}"[:80]
        result = engine.continue_chat(
            ChatEngineRequest(
                message=message,
                existing_payload=existing_payload,
                user_id=int(user.pk),
                metadata={
                    "surface": "ai_nutrition_intake",
                    "tool_user": user,
                    "conversation_id": conversation_id,
                    "turn_id": turn_id,
                    "action_type": OUTCOME_FIRST_ACTION_TYPE,
                    "chat_engine_mode": "llm",
                    "outcome_first_validation": True,
                },
            )
        )
        if not isinstance(result.state, NutritionConversationState):
            raise RuntimeError(
                "Outcome-first validation engine returned an unsupported conversation state."
            )
        existing_payload = serialize_conversation(result.state)
        cards = _card_counts(result.state)
        metadata = dict(result.metadata or {})
        turn = RealProviderValidationTurn(
            index=index,
            turn_id=turn_id,
            user_message=message,
            assistant_message=str(result.assistant_text or "").strip(),
            engine_name=str(result.engine_name or ""),
            brief_snapshot=_brief_snapshot(result.state),
            semantic_intent=str(metadata.get("llm_semantic_intent") or ""),
            semantic_missing_slots=tuple(metadata.get("llm_semantic_missing_slots") or ()),
            tool_results=tuple(dict(item) for item in list(metadata.get("llm_tool_results") or [])),
            card_counts=cards,
            card_deltas={key: cards[key] - previous_cards[key] for key in cards},
            fallback=bool(metadata.get("llm_degraded")),
            fallback_reason=str(metadata.get("llm_degraded_reason") or ""),
            deterministic_runtime_invoked=bool(metadata.get("deterministic_runtime_invoked")),
            provider=str(metadata.get("llm_provider") or ""),
            model=str(metadata.get("llm_model") or ""),
            usage_observability=dict(metadata.get("usage_observability") or {}),
            provider_parse_error=str(metadata.get("llm_provider_parse_error") or ""),
            provider_contract_repair_attempted=bool(
                metadata.get("llm_provider_contract_repair_attempted")
            ),
            provider_native_tool_transport=bool(
                metadata.get("llm_provider_native_tool_transport")
            ),
            provider_native_tool_calls=int(
                metadata.get("llm_provider_native_tool_calls") or 0
            ),
            provider_text_parse_ignored_due_to_native_tools=bool(
                metadata.get("llm_provider_text_parse_ignored_due_to_native_tools")
            ),
            provider_incomplete_reasons=tuple(
                metadata.get("llm_provider_incomplete_reasons") or ()
            ),
            provider_final_incomplete_reason=str(
                metadata.get("llm_provider_final_incomplete_reason") or ""
            ),
            tool_followup_local_ack=bool(
                metadata.get("llm_tool_followup_local_ack")
            ),
            tool_followup_local_ack_policy=str(
                metadata.get("llm_tool_followup_local_ack_policy") or ""
            ),
            provider_tool_followup_failed=bool(
                metadata.get("llm_provider_tool_followup_failed")
            ),
            provider_tool_followup_error_status=_optional_int(
                metadata.get("llm_provider_tool_followup_error_status")
            ),
            provider_tool_followup_error_type=str(
                metadata.get("llm_provider_tool_followup_error_provider_type") or ""
            ),
            provider_tool_followup_error_code=str(
                metadata.get("llm_provider_tool_followup_error_code") or ""
            ),
            provider_tool_followup_error_message=str(
                metadata.get("llm_provider_tool_followup_error_message") or ""
            )[:600],
            provider_tool_followup_error_param=str(
                metadata.get("llm_provider_tool_followup_error_param") or ""
            ),
            provider_tool_followup_error_request_id=str(
                metadata.get("llm_provider_tool_followup_error_request_id") or ""
            ),
        )
        turns.append(turn)
        previous_cards = cards

    usage_events = tuple(_usage_events_for_conversation(conversation_id))
    checks = _scenario_checks(scenario=scenario, turns=turns, usage_events=usage_events)
    return RealProviderValidationScenarioResult(
        scenario=scenario,
        conversation_id=conversation_id,
        turns=tuple(turns),
        usage_events=usage_events,
        checks=tuple(checks),
    )


def _scenario_checks(
    *,
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
    usage_events: Sequence[Mapping[str, Any]],
) -> list[RealProviderValidationCheck]:
    checks: list[RealProviderValidationCheck] = []
    visible_blob = "\n".join(turn.assistant_message for turn in turns).lower()
    leaked = [
        marker
        for marker in OUTCOME_FIRST_FORBIDDEN_VISIBLE_MARKERS
        if marker in visible_blob
    ]
    checks.append(
        _check(
            "visible_boundary",
            not leaked and all(turn.assistant_message for turn in turns),
            "visible responses are non-empty and contain no internal envelope markers"
            if not leaked
            else f"visible text leaked internal marker(s): {leaked}",
        )
    )
    checks.append(
        _check(
            "llm_only_runtime",
            all(not turn.deterministic_runtime_invoked for turn in turns),
            "deterministic runtime was not invoked"
            if all(not turn.deterministic_runtime_invoked for turn in turns)
            else "deterministic runtime was invoked during live validation",
        )
    )
    checks.append(_provider_health_check(turns, usage_events))
    checks.append(_natural_provider_contract_check(turns))
    checks.append(_expected_brief_check(scenario, turns))
    if scenario.profile_preflight_facts or scenario.profile_preflight_missing_fields:
        checks.append(_profile_preflight_check(scenario))
    checks.append(_stable_facts_check(scenario, turns))
    checks.append(_known_facts_not_reasked_check(scenario, turns))
    checks.append(_brief_transition_check(scenario, turns))
    checks.append(_tool_contract_check(scenario, turns))
    checks.append(_behavioral_surface_check(scenario, turns))
    checks.append(_response_repetition_check(scenario, turns))
    checks.append(_tool_result_grounding_check(turns))
    checks.append(_provider_followup_health_check(turns))
    checks.append(_post_tool_fallback_pacing_check(turns))
    checks.append(_card_pacing_check(scenario, turns))
    checks.append(_usage_observability_check(turns, usage_events))
    checks.append(
        RealProviderValidationCheck(
            key="manual_ux_review",
            passed=True,
            detail=f"{len(scenario.manual_review_prompts)} qualitative prompt(s) require human review",
            severity="manual",
        )
    )
    return checks


def _provider_health_check(
    turns: Sequence[RealProviderValidationTurn],
    usage_events: Sequence[Mapping[str, Any]],
) -> RealProviderValidationCheck:
    """Treat persisted usage events as authoritative provider evidence.

    Chat-surface metadata is useful for diagnostics, but older adapters may omit
    it even when the provider call completed and AIUsageEvent was recorded. A
    technical fallback still fails immediately; otherwise each turn may prove
    provider health through either safe turn metadata or its completed event.
    """

    completed_by_turn = {
        str(event.get("turn_id") or ""): event
        for event in usage_events
        if event.get("status") == "completed"
        and str(event.get("provider") or "").strip().lower() not in {"", "fake"}
    }
    failures: list[str] = []
    metadata_count = 0
    event_count = 0
    for turn in turns:
        if turn.fallback:
            failures.append(f"turn {turn.index}: technical fallback ({turn.fallback_reason or 'unknown'})")
            continue
        metadata_ok = str(turn.provider or "").strip().lower() not in {"", "fake"}
        event = completed_by_turn.get(_turn_id_for_validation_turn(turn))
        event_ok = event is not None
        metadata_count += int(metadata_ok)
        event_count += int(event_ok)
        if not metadata_ok and not event_ok:
            failures.append(f"turn {turn.index}: no real-provider evidence")
    return _check(
        "provider_health",
        not failures,
        (
            f"real provider confirmed for all {len(turns)} turn(s) "
            f"(metadata={metadata_count}, usage_events={event_count})"
            if not failures
            else f"provider health failures: {failures}"
        ),
    )


def _turn_id_for_validation_turn(turn: RealProviderValidationTurn) -> str:
    return str(turn.turn_id or "")


def _natural_provider_contract_check(
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    """Validate natural visible text plus native provider action transport.

    Tool operations must arrive through provider-native function calls. The
    final visible response must be natural text; there is no JSON envelope for
    the model to complete or the user interface to decode.
    """

    failures: list[str] = []
    repair_count = 0
    native_call_count = 0
    for turn in turns:
        repair_count += int(turn.provider_contract_repair_attempted)
        native_call_count += int(turn.provider_native_tool_calls or 0)
        if turn.provider_parse_error:
            failures.append(f"turn {turn.index}: final text parse error")
        if turn.provider_final_incomplete_reason:
            failures.append(
                f"turn {turn.index}: final incomplete={turn.provider_final_incomplete_reason}"
            )
        normalized_message = turn.assistant_message.strip()
        if normalized_message in {"{", "[", "```json", "```"}:
            failures.append(f"turn {turn.index}: visibly truncated response")
        if normalized_message.startswith(("{", "[")) and any(
            marker in normalized_message
            for marker in ('"assistant_message"', '"tool_requests"', '"missing_slots"')
        ):
            failures.append(f"turn {turn.index}: visible JSON response envelope")
        if turn.tool_results and not turn.provider_native_tool_transport:
            failures.append(
                f"turn {turn.index}: tool results without native function-call transport"
            )
        if turn.tool_results and turn.provider_native_tool_calls < 1:
            failures.append(f"turn {turn.index}: tool results without recorded native calls")
    return _check(
        "natural_provider_contract",
        not failures,
        (
            f"all {len(turns)} provider turn(s) validated; "
            f"native function calls={native_call_count}; repair retries={repair_count}"
            if not failures
            else f"provider transport failures: {failures}; "
            f"native function calls={native_call_count}; repair retries={repair_count}"
        ),
    )


def _expected_brief_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    final = turns[-1].brief_snapshot if turns else {}
    mismatches = {
        key: {"expected": expected, "actual": final.get(key)}
        for key, expected in scenario.expected_final_brief.items()
        if final.get(key) != expected
    }
    return _check(
        "expected_brief",
        not mismatches,
        f"{len(scenario.expected_final_brief)} expected brief field(s) matched"
        if not mismatches
        else f"brief mismatch: {mismatches}",
    )


def _stable_facts_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    failures: list[str] = []
    for field_name in scenario.stable_brief_fields:
        captured = False
        captured_value: Any = None
        for turn in turns:
            value = turn.brief_snapshot.get(field_name)
            if not captured and not _is_empty(value):
                captured = True
                captured_value = value
                continue
            if captured and value != captured_value:
                failures.append(f"{field_name}: {captured_value!r} -> {value!r}")
                break
        if not captured:
            failures.append(f"{field_name}: never captured")
    return _check(
        "stable_captured_facts",
        not failures,
        f"{len(scenario.stable_brief_fields)} captured fact(s) remained stable"
        if not failures
        else f"unstable facts: {failures}",
    )


def _known_facts_not_reasked_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    watched = set(scenario.fields_not_reasked_after_capture)
    known: set[str] = set()
    failures: list[str] = []
    for turn in turns:
        known_this_turn = known.union(
            field_name
            for field_name in watched
            if not _is_empty(turn.brief_snapshot.get(field_name))
        )
        repeated = watched.intersection(known_this_turn).intersection(turn.semantic_missing_slots)
        if repeated:
            failures.append(f"turn {turn.index}: semantic missing {sorted(repeated)}")

        normalized_message = " ".join(turn.assistant_message.lower().split())
        question_fragments = tuple(
            fragment.strip()
            for fragment in normalized_message.replace("!", "?").split("?")
            if fragment.strip()
        )
        for field_name in sorted(known_this_turn):
            markers = tuple(scenario.visible_reask_markers.get(field_name) or ())
            matched = next(
                (
                    marker
                    for marker in markers
                    if any(marker.lower() in fragment for fragment in question_fragments)
                ),
                "",
            )
            if matched:
                failures.append(
                    f"turn {turn.index}: visibly re-asked {field_name} via {matched!r}"
                )
        known = known_this_turn
    return _check(
        "known_facts_not_reasked",
        not failures,
        f"{len(watched)} watched field(s) were neither marked missing nor visibly re-asked"
        if not failures
        else f"known fields were re-requested: {failures}",
    )


def _brief_transition_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    failures: dict[str, Any] = {}
    for field_name, expected in scenario.expected_brief_transitions.items():
        actual = _compressed_values(turn.brief_snapshot.get(field_name) for turn in turns)
        if not _is_subsequence(list(expected), actual):
            failures[field_name] = {"expected": list(expected), "actual": actual}
    return _check(
        "brief_transitions",
        not failures,
        f"{len(scenario.expected_brief_transitions)} intentional transition(s) matched"
        if not failures
        else f"transition mismatch: {failures}",
    )


def _tool_contract_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    results = [item for turn in turns for item in turn.tool_results]
    actual_names = {str(item.get("tool_name") or "") for item in results}
    missing = sorted(set(scenario.required_tool_names).difference(actual_names))
    error_failures: list[str] = []
    for tool_name, expected_status in scenario.expected_tool_errors.items():
        matching = [item for item in results if item.get("tool_name") == tool_name]
        if not matching or not any(item.get("status") == expected_status for item in matching):
            error_failures.append(f"{tool_name}:{expected_status}")
    passed = not missing and not error_failures
    detail = f"{len(actual_names)} distinct tool(s) satisfied the scenario contract"
    if not passed:
        detail = f"missing tools={missing}; missing expected error result(s)={error_failures}"
    return _check("tool_contract", passed, detail)



def _behavioral_surface_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    actual_tools = {name for turn in turns for name in turn.tool_names}
    forbidden_tools = sorted(set(scenario.forbidden_tool_names).intersection(actual_tools))
    visible_blob = "\n".join(turn.assistant_message.lower() for turn in turns)
    leaked_fragments = [
        fragment
        for fragment in scenario.forbidden_visible_fragments
        if fragment and fragment.lower() in visible_blob
    ]
    tool_call_count = sum(len(turn.tool_names) for turn in turns)
    too_many_tools = scenario.max_tool_calls is not None and tool_call_count > scenario.max_tool_calls
    passed = not forbidden_tools and not leaked_fragments and not too_many_tools
    details = []
    if forbidden_tools:
        details.append(f"forbidden tools executed: {', '.join(forbidden_tools)}")
    if leaked_fragments:
        details.append(f"forbidden visible fragments: {', '.join(leaked_fragments)}")
    if too_many_tools:
        details.append(f"tool calls {tool_call_count} exceeded maximum {scenario.max_tool_calls}")
    if not details:
        details.append("tool restraint and product-language boundary were respected")
    return _check("behavioral_surface", passed, "; ".join(details))


def _response_repetition_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    limit = scenario.max_repeated_opening_count
    if limit is None:
        return _check("response_repetition", True, "scenario does not define an opening repetition limit")
    openings = []
    for turn in turns:
        text = " ".join(str(turn.assistant_message or "").strip().split())
        if not text:
            continue
        first_sentence = text.split(".", 1)[0].strip().lower()
        openings.append(first_sentence[:80])
    counts = {opening: openings.count(opening) for opening in set(openings)}
    repeated = {opening: count for opening, count in counts.items() if count > limit}
    passed = not repeated
    detail = (
        "assistant openings stayed within the configured repetition limit"
        if passed
        else "repeated openings: " + ", ".join(f"{opening!r} x{count}" for opening, count in sorted(repeated.items()))
    )
    return _check("response_repetition", passed, detail)

def _tool_result_grounding_check(
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    """Reject claims that tools are unavailable after a real tool result exists."""

    unavailable_markers = (
        "no tengo ejecución de herramientas",
        "no tengo herramientas disponibles",
        "no puedo ejecutar herramientas",
        "no puedo usar la herramienta",
        "no tengo acceso a herramientas",
    )
    failures: list[str] = []
    for turn in turns:
        if not turn.tool_results:
            continue
        normalized = " ".join(turn.assistant_message.lower().split())
        matched = [marker for marker in unavailable_markers if marker in normalized]
        if matched:
            failures.append(f"turn {turn.index}: contradicted executed tool result")
    return _check(
        "tool_result_grounding",
        not failures,
        "assistant text remained grounded in available tool results"
        if not failures
        else f"tool grounding failures: {failures}",
    )




def _provider_followup_health_check(
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    """Fail the live gate whenever a tool turn needs a local acknowledgement.

    A local acknowledgement is a resilience path, not a healthy provider-written
    completion. PT04 treats both provider failures and technical-limit fallbacks
    as release-blocking degradations.
    """

    failures: list[str] = []
    for turn in turns:
        healthy_tool_turn = bool(turn.tool_results) and not (
            turn.tool_followup_local_ack or turn.provider_tool_followup_failed
        )
        if healthy_tool_turn:
            matched_ack = next(
                (
                    fragment
                    for fragment in POST_TOOL_LOCAL_ACK_FRAGMENTS
                    if fragment in turn.assistant_message
                ),
                "",
            )
            if matched_ack:
                failures.append(
                    f"turn {turn.index}: healthy tool turn reproduced local acknowledgement "
                    f"{matched_ack!r}"
                )
            continue
        if not turn.tool_followup_local_ack and not turn.provider_tool_followup_failed:
            continue
        detail = " ".join(
            part
            for part in (
                "local_ack=true" if turn.tool_followup_local_ack else "",
                f"policy={turn.tool_followup_local_ack_policy}"
                if turn.tool_followup_local_ack_policy
                else "",
                "provider_followup_failed=true"
                if turn.provider_tool_followup_failed
                else "",
                f"status={turn.provider_tool_followup_error_status}"
                if turn.provider_tool_followup_error_status is not None
                else "",
                f"type={turn.provider_tool_followup_error_type}"
                if turn.provider_tool_followup_error_type
                else "",
                f"code={turn.provider_tool_followup_error_code}"
                if turn.provider_tool_followup_error_code
                else "",
                f"param={turn.provider_tool_followup_error_param}"
                if turn.provider_tool_followup_error_param
                else "",
                f"request_id={turn.provider_tool_followup_error_request_id}"
                if turn.provider_tool_followup_error_request_id
                else "",
                f"message={turn.provider_tool_followup_error_message}"
                if turn.provider_tool_followup_error_message
                else "",
            )
            if part
        )
        failures.append(
            f"turn {turn.index}: post-tool response degraded"
            + (f" ({detail})" if detail else "")
        )

    return _check(
        "provider_followup_health",
        not failures,
        "all tool turns received provider-written follow-up responses"
        if not failures
        else f"post-tool degradations: {failures}",
    )


def _post_tool_fallback_pacing_check(
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    """Keep technical post-tool fallbacks state-only and non-interviewing.

    The normal provider remains free to ask useful questions. This invariant
    applies only when My Scoope had to compose a local acknowledgement after a
    validated tool result because the provider follow-up failed or exceeded a
    limit. That technical fallback may report controlled state, but it must not
    choose the next question or recreate a deterministic intake agenda.
    """

    fallback_turns = [turn for turn in turns if turn.tool_followup_local_ack]
    failures: list[str] = []
    forbidden_markers = (
        "para seguir",
        "cuéntame si quieres usar tu ficha",
        "prefieres entregar datos nuevos",
    )
    for turn in fallback_turns:
        if turn.tool_followup_local_ack_policy != "state_ack_only.v2":
            failures.append(
                f"turn {turn.index}: unexpected local-ack policy "
                f"{turn.tool_followup_local_ack_policy or 'missing'}"
            )
        normalized = " ".join(turn.assistant_message.lower().split())
        if "?" in turn.assistant_message or any(marker in normalized for marker in forbidden_markers):
            failures.append(f"turn {turn.index}: local fallback selected a follow-up question")

    return _check(
        "post_tool_fallback_pacing",
        not failures,
        (
            f"{len(fallback_turns)} post-tool local acknowledgement(s) remained state-only"
            if not failures
            else f"post-tool fallback pacing failures: {failures}"
        ),
    )

def _card_pacing_check(
    scenario: RealProviderValidationScenario,
    turns: Sequence[RealProviderValidationTurn],
) -> RealProviderValidationCheck:
    update_tools = {
        "profile": "update_profile_draft",
        "preference": "update_preference_draft",
        "proposal_preferences": "update_proposal_preferences",
    }
    share_tools = {
        "profile": {"read_user_profile_context", "share_profile_draft_card"},
        "preference": {"share_preference_draft_card"},
        "proposal_preferences": {"share_proposal_preferences_card"},
    }
    failures: list[str] = []
    for turn in turns:
        names = set(turn.tool_names)
        for kind, update_tool in update_tools.items():
            if update_tool in names and not names.intersection(share_tools[kind]) and turn.card_deltas.get(kind, 0):
                failures.append(f"turn {turn.index}: {update_tool} rendered {kind} card")
    final_cards = turns[-1].card_counts if turns else {}
    for kind, minimum in scenario.min_final_card_counts.items():
        if int(final_cards.get(kind, 0)) < int(minimum):
            failures.append(f"final {kind} cards below minimum {minimum}: {final_cards.get(kind, 0)}")
    for kind, maximum in scenario.max_final_card_counts.items():
        if int(final_cards.get(kind, 0)) > int(maximum):
            failures.append(f"final {kind} cards above maximum {maximum}: {final_cards.get(kind, 0)}")
    return _check(
        "card_pacing",
        not failures,
        "silent updates and explicit shares respected card pacing"
        if not failures
        else f"card pacing failures: {failures}",
    )


def _usage_observability_check(
    turns: Sequence[RealProviderValidationTurn],
    usage_events: Sequence[Mapping[str, Any]],
) -> RealProviderValidationCheck:
    """Use persisted AIUsageEvent rows as the hard source of truth.

    Safe turn metadata is retained as a diagnostic signal, but a missing bridge
    field must not classify a successfully persisted provider call as a usage
    regression.
    """

    recorded_turns = sum(1 for turn in turns if bool(turn.usage_observability.get("recorded")))
    event_count = len(usage_events)
    completed = sum(1 for event in usage_events if event.get("status") == "completed")
    unique_turn_ids = {str(event.get("turn_id") or "") for event in usage_events}
    expected_turn_ids = {str(turn.turn_id or "") for turn in turns}
    passed = (
        event_count == len(turns)
        and completed == len(turns)
        and unique_turn_ids == expected_turn_ids
    )
    return _check(
        "usage_observability",
        passed,
        (
            f"database usage recorded for all {len(turns)} turn(s); "
            f"safe metadata available on {recorded_turns}/{len(turns)}"
            if passed
            else (
                f"turns={len(turns)}, metadata_recorded={recorded_turns}, "
                f"database_events={event_count}, completed={completed}, "
                f"turn_ids_match={unique_turn_ids == expected_turn_ids}"
            )
        ),
    )


def _usage_events_for_conversation(conversation_id: str) -> list[dict[str, Any]]:
    return [
        {
            "id": event.id,
            "turn_id": event.turn_id,
            "status": event.status,
            "provider": event.provider,
            "model": event.model_name,
            "input_tokens": event.input_tokens,
            "cached_input_tokens": event.cached_input_tokens,
            "output_tokens": event.output_tokens,
            "total_tokens": event.total_tokens,
            "estimated_cost_usd": str(event.estimated_cost_usd) if event.estimated_cost_usd is not None else None,
            "charged_credits": event.charged_credits,
            "tool_calls_count": event.tool_calls_count,
            "latency_ms": event.latency_ms,
            "error_type": event.error_type,
        }
        for event in AIUsageEvent.objects.filter(conversation_id=conversation_id).order_by("created_at", "id")
    ]


def _usage_and_credit_snapshot(*, user: Any, run_id: str) -> dict[str, Any]:
    conversation_prefix = f"outcome-{run_id[:20]}-"
    events = AIUsageEvent.objects.filter(user=user, conversation_id__startswith=conversation_prefix)
    ledgers = AICreditLedger.objects.filter(user=user, usage_event__in=events)
    quota = AIUserCreditQuota.objects.filter(user=user).order_by("-period", "-updated_at").first()
    return {
        "event_count": events.count(),
        "completed_count": events.filter(status=AIUsageEvent.Status.COMPLETED).count(),
        "error_count": events.filter(status=AIUsageEvent.Status.ERROR).count(),
        "blocked_count": events.filter(status=AIUsageEvent.Status.BLOCKED).count(),
        "input_tokens": sum(int(value or 0) for value in events.values_list("input_tokens", flat=True)),
        "cached_input_tokens": sum(int(value or 0) for value in events.values_list("cached_input_tokens", flat=True)),
        "output_tokens": sum(int(value or 0) for value in events.values_list("output_tokens", flat=True)),
        "total_tokens": sum(int(value or 0) for value in events.values_list("total_tokens", flat=True)),
        "estimated_cost_usd": sum(
            (value or Decimal("0")) for value in events.values_list("estimated_cost_usd", flat=True)
        ),
        "charged_credits": sum(int(value or 0) for value in events.values_list("charged_credits", flat=True)),
        "ledger_count": ledgers.count(),
        "quota_credits_used": int(getattr(quota, "credits_used", 0) or 0),
        "quota_period": str(getattr(quota, "period", "") or ""),
        "quota_plan_code": str(getattr(quota, "plan_code", "") or ""),
    }


def _usage_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    keys = (
        "event_count",
        "completed_count",
        "error_count",
        "blocked_count",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "total_tokens",
    )
    payload = {key: int(after.get(key, 0) or 0) - int(before.get(key, 0) or 0) for key in keys}
    payload["estimated_cost_usd"] = str(
        Decimal(after.get("estimated_cost_usd", 0) or 0) - Decimal(before.get("estimated_cost_usd", 0) or 0)
    )
    return payload


def _credit_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "charged_credits": int(after.get("charged_credits", 0) or 0) - int(before.get("charged_credits", 0) or 0),
        "ledger_entries": int(after.get("ledger_count", 0) or 0) - int(before.get("ledger_count", 0) or 0),
        "quota_credits_used_delta": int(after.get("quota_credits_used", 0) or 0)
        - int(before.get("quota_credits_used", 0) or 0),
        "quota_period": str(after.get("quota_period") or ""),
        "quota_plan_code": str(after.get("quota_plan_code") or ""),
    }


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
        "complexity_level": brief.complexity_level,
        "budget_level": brief.budget_level,
        "style_preferences": list(brief.style_preferences or []),
        "excluded_foods": list(brief.excluded_foods or []),
        "preferred_foods": list(brief.preferred_foods or []),
        "field_sources": dict(brief.field_sources or {}),
        "is_ready_for_proposal": state.is_ready_for_proposal,
    }


def _card_counts(state: NutritionConversationState) -> dict[str, int]:
    return {
        "profile": sum(1 for message in state.messages if message.profile_draft_card),
        "preference": sum(1 for message in state.messages if message.preference_draft_card),
        "proposal_preferences": sum(1 for message in state.messages if message.proposal_preferences_card),
    }


def _select_scenarios(keys: Sequence[str] | None) -> tuple[RealProviderValidationScenario, ...]:
    catalog = built_in_real_provider_scenarios()
    selected_keys = tuple(keys or catalog.keys())
    unknown = [key for key in selected_keys if key not in catalog]
    if unknown:
        raise ValueError(
            f"Unknown outcome-first validation scenario(s): {', '.join(unknown)}"
        )
    return tuple(catalog[key] for key in selected_keys)


def _scenario_result_as_dict(result: RealProviderValidationScenarioResult) -> dict[str, Any]:
    return {
        "key": result.scenario.key,
        "description": result.scenario.description,
        "status": "automated_checks_passed" if result.passed else "hard_regression",
        "conversation_id": result.conversation_id,
        "checks": [
            {
                "key": check.key,
                "severity": check.severity,
                "passed": check.passed,
                "detail": check.detail,
            }
            for check in result.checks
        ],
        "manual_review_prompts": list(result.scenario.manual_review_prompts),
        "profile_preflight": {
            "available_facts": dict(result.scenario.profile_preflight_facts),
            "missing_fields": list(result.scenario.profile_preflight_missing_fields),
        }
        if result.scenario.profile_preflight_facts or result.scenario.profile_preflight_missing_fields
        else {},
        "turns": [
            {
                "index": turn.index,
                "user": turn.user_message,
                "assistant": turn.assistant_message,
                "semantic_intent": turn.semantic_intent,
                "semantic_missing_slots": list(turn.semantic_missing_slots),
                "tools": [dict(item) for item in turn.tool_results],
                "cards": dict(turn.card_counts),
                "card_deltas": dict(turn.card_deltas),
                "brief": dict(turn.brief_snapshot),
                "provider": turn.provider,
                "model": turn.model,
                "fallback": turn.fallback,
                "fallback_reason": turn.fallback_reason,
                "deterministic_runtime_invoked": turn.deterministic_runtime_invoked,
                "usage_observability": dict(turn.usage_observability),
                "provider_contract": {
                    "parse_error": bool(turn.provider_parse_error),
                    "contract_repair_attempted": turn.provider_contract_repair_attempted,
                    "native_tool_transport": turn.provider_native_tool_transport,
                    "native_tool_calls": turn.provider_native_tool_calls,
                    "text_parse_ignored_due_to_native_tools": (
                        turn.provider_text_parse_ignored_due_to_native_tools
                    ),
                    "incomplete_reasons": list(turn.provider_incomplete_reasons),
                    "final_incomplete_reason": turn.provider_final_incomplete_reason,
                },
                "post_tool_fallback": {
                    "local_ack": turn.tool_followup_local_ack,
                    "policy": turn.tool_followup_local_ack_policy,
                    "provider_followup_failed": turn.provider_tool_followup_failed,
                    "provider_error": {
                        "status": turn.provider_tool_followup_error_status,
                        "type": turn.provider_tool_followup_error_type,
                        "code": turn.provider_tool_followup_error_code,
                        "message": turn.provider_tool_followup_error_message,
                        "param": turn.provider_tool_followup_error_param,
                        "request_id": turn.provider_tool_followup_error_request_id,
                    }
                    if turn.provider_tool_followup_failed
                    else {},
                },
            }
            for turn in result.turns
        ],
        "usage_events": [dict(item) for item in result.usage_events],
    }


def _check(key: str, passed: bool, detail: str) -> RealProviderValidationCheck:
    return RealProviderValidationCheck(key=key, passed=bool(passed), detail=detail, severity="hard")



def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (TypeError, ValueError):
        return None


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _compressed_values(values: Iterable[Any]) -> list[Any]:
    compressed: list[Any] = []
    for value in values:
        if _is_empty(value):
            continue
        if not compressed or compressed[-1] != value:
            compressed.append(value)
    return compressed


def _is_subsequence(expected: Sequence[Any], actual: Sequence[Any]) -> bool:
    iterator = iter(actual)
    return all(any(candidate == expected_value for candidate in iterator) for expected_value in expected)


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""
