from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import time
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Mapping

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.services.credits import (
    AccountCreditsFrozen,
    InsufficientAccountCredits,
    consume_account_credit_reservation,
    get_or_create_current_wallet,
    release_account_credit_reservation,
    reserve_account_credits,
)
from ai_assistant.application.pricing import estimate_cost_usd
from ai_assistant.models import AIUsageEvent
from notas.domain.models import FoodLabelAIAnalysis

ACTION_TYPE = "nutrition_label.scan"
REFERENCE_TYPE = "nutrition_label_ai_analysis"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class NutritionLabelAIError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(code)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class ProviderCall:
    model: str
    stage: str
    elapsed_ms: int
    data: Mapping[str, Any] | None = None
    error_type: str = ""

    @property
    def usage(self) -> Mapping[str, Any]:
        value = self.data.get("usage") if self.data else None
        return value if isinstance(value, Mapping) else {}

    @property
    def estimated_cost_usd(self) -> Decimal | None:
        if not self.data:
            return None
        usage = self.usage
        details = usage.get("input_tokens_details")
        cached = details.get("cached_tokens") if isinstance(details, Mapping) else usage.get("cached_input_tokens")
        return estimate_cost_usd(
            provider="openai",
            model=str(self.data.get("model") or self.model),
            input_tokens=_safe_int(usage.get("input_tokens")),
            cached_input_tokens=_safe_int(cached),
            output_tokens=_safe_int(usage.get("output_tokens")),
        )


LABEL_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "status",
        "product_name",
        "basis",
        "serving_size_g",
        "energy_value",
        "energy_unit",
        "protein_g",
        "carbs_g",
        "fat_g",
        "saturated_fat_g",
        "sugar_g",
        "fiber_g",
        "sodium_value",
        "sodium_unit",
        "confidence",
    ],
    "properties": {
        "status": {"type": "string", "enum": ["resolved", "ambiguous", "not_nutrition_label", "image_unreadable"]},
        "product_name": {"type": ["string", "null"]},
        "basis": {"type": "string", "enum": ["per_100g", "per_serving", "per_100ml", "unknown"]},
        "serving_size_g": {"type": ["number", "null"]},
        "energy_value": {"type": ["number", "null"]},
        "energy_unit": {"type": ["string", "null"], "enum": ["kcal", "kJ", None]},
        "protein_g": {"type": ["number", "null"]},
        "carbs_g": {"type": ["number", "null"]},
        "fat_g": {"type": ["number", "null"]},
        "saturated_fat_g": {"type": ["number", "null"]},
        "sugar_g": {"type": ["number", "null"]},
        "fiber_g": {"type": ["number", "null"]},
        "sodium_value": {"type": ["number", "null"]},
        "sodium_unit": {"type": ["string", "null"], "enum": ["mg", "g", None]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}

LABEL_PROMPT = """You extract printed nutrition facts from a package photo.
Return only the strict JSON result. Never infer values that are not visible. Ignore daily-value percentages.
Prefer the column explicitly headed per 100 g; otherwise use the per-serving column and its printed serving weight.
Keep decimal separators and units semantically correct. Sodium may be printed as salt: do not convert salt to sodium.
Set status to resolved only when protein, carbohydrates, fat and their basis are clearly legible.
If this is not a nutrition label, the image is unreadable, or the basis is uncertain, report that status instead of guessing.
The user will review every resulting field before saving."""


def nutrition_label_scan_cost() -> int:
    return max(1, int(getattr(settings, "NUTRITION_LABEL_AI_CREDITS_PER_SCAN", 2)))


def validate_retained_label_image(
    *, user, analysis_id: str, image_base64: str, image_content_type: str
) -> tuple[bytes, str, str]:
    analysis = FoodLabelAIAnalysis.objects.filter(
        public_id=analysis_id,
        user=user,
        status=FoodLabelAIAnalysis.STATUS_COMPLETED,
    ).first()
    if analysis is None:
        raise NutritionLabelAIError(
            "nutrition_label_analysis_not_found",
            "La digitalización ya no está disponible para guardar su imagen.",
            404,
        )
    image_bytes, content_type = _decode_image(image_base64, image_content_type)
    digest = hashlib.sha256(image_bytes).hexdigest()
    if digest != analysis.image_sha256:
        raise NutritionLabelAIError(
            "nutrition_label_image_mismatch",
            "La imagen no corresponde a la digitalización revisada.",
            409,
        )
    return image_bytes, content_type, digest


def analyze_nutrition_label(
    *,
    user,
    image_base64: str,
    image_content_type: str,
    image_width: int,
    image_height: int,
    idempotency_key: str,
    consent_to_ai_processing: bool,
    local_candidate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not consent_to_ai_processing:
        raise NutritionLabelAIError(
            "nutrition_label_ai_consent_required",
            "Debes autorizar el procesamiento de esta foto para digitalizarla con IA.",
        )
    clean_key = str(idempotency_key or "").strip()
    if not 8 <= len(clean_key) <= 120:
        raise NutritionLabelAIError("nutrition_label_ai_key_invalid", "La solicitud de digitalización no es válida.")
    image_bytes, content_type = _decode_image(image_base64, image_content_type)
    if not 320 <= int(image_width or 0) <= 10_000 or not 320 <= int(image_height or 0) <= 10_000:
        raise NutritionLabelAIError(
            "nutrition_label_image_dimensions_invalid", "La imagen es demasiado pequeña o no es válida."
        )

    image_sha = hashlib.sha256(image_bytes).hexdigest()
    safe_local = _safe_local_candidate(local_candidate)
    request_hash = hashlib.sha256(
        json.dumps(
            {"image_sha256": image_sha, "content_type": content_type, "local_candidate": safe_local},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    analysis, replay = _start_analysis(
        user=user,
        idempotency_key=clean_key,
        request_hash=request_hash,
        image_sha=image_sha,
    )
    if replay:
        result = dict(analysis.result_payload)
        result["available_credits"] = get_or_create_current_wallet(user=user).available_credits
        return result

    credits = nutrition_label_scan_cost()
    reference_id = f"{analysis.public_id}:{analysis.attempt_count}"
    credits_enabled = bool(getattr(settings, "AI_ASSISTANT_CREDITS_ENABLED", False))
    _reserve_scan_credits(
        user=user,
        analysis=analysis,
        credits=credits,
        enabled=credits_enabled,
        reference_id=reference_id,
    )

    calls: list[ProviderCall] = []
    primary_model = str(getattr(settings, "NUTRITION_LABEL_AI_PRIMARY_MODEL", "gpt-5.6-luna") or "").strip()
    escalation_model = str(getattr(settings, "NUTRITION_LABEL_AI_ESCALATION_MODEL", "gpt-5.6-sol") or "").strip()
    analysis.primary_model = primary_model
    analysis.save(update_fields=["primary_model", "updated_at"])

    primary_payload, primary_error = _try_provider(
        image_bytes=image_bytes,
        content_type=content_type,
        model=primary_model,
        stage="primary",
        calls=calls,
    )
    primary_candidate, primary_validation_error = _normalize_provider_payload(primary_payload)
    escalation_reason = primary_error or primary_validation_error
    if primary_candidate and not escalation_reason:
        escalation_reason = _escalation_reason(primary_candidate, safe_local)

    selected = primary_candidate
    escalated = bool(escalation_reason)
    stronger_selected = False
    if escalated:
        stronger_payload, stronger_error = _try_provider(
            image_bytes=image_bytes,
            content_type=content_type,
            model=escalation_model,
            stage="escalation",
            calls=calls,
        )
        stronger_candidate, stronger_validation_error = _normalize_provider_payload(stronger_payload)
        stronger_quality_error = _escalation_reason(stronger_candidate, safe_local) if stronger_candidate else ""
        if stronger_candidate and not stronger_quality_error:
            selected = stronger_candidate
            stronger_selected = True
        else:
            failure = (
                stronger_error
                or stronger_validation_error
                or stronger_quality_error
                or escalation_reason
                or "unresolved"
            )
            _record_calls(user=user, analysis=analysis, calls=calls, selected_stage="")
            _release_if_needed(user=user, enabled=credits_enabled, reference_id=reference_id, reason=failure)
            _fail_analysis(analysis, failure, calls=calls, escalated=True, escalation_reason=escalation_reason)
            raise NutritionLabelAIError(
                "nutrition_label_could_not_resolve",
                "No pudimos leer esta etiqueta con suficiente seguridad. Prueba otra foto o completa los valores manualmente.",
            )

    if selected is None:
        failure = escalation_reason or "unresolved"
        _record_calls(user=user, analysis=analysis, calls=calls, selected_stage="")
        _release_if_needed(user=user, enabled=credits_enabled, reference_id=reference_id, reason=failure)
        _fail_analysis(analysis, failure, calls=calls, escalated=escalated, escalation_reason=escalation_reason)
        raise NutritionLabelAIError(
            "nutrition_label_could_not_resolve",
            "No pudimos leer esta etiqueta con suficiente seguridad. Prueba otra foto o completa los valores manualmente.",
        )

    selected_stage = "escalation" if stronger_selected else "primary"
    try:
        usage_events = _record_calls(user=user, analysis=analysis, calls=calls, selected_stage=selected_stage)
    except Exception:
        usage_events = []
    total_cost = sum((call.estimated_cost_usd or Decimal("0")) for call in calls)
    selected_call = next((call for call in reversed(calls) if call.stage == selected_stage), calls[0])
    try:
        with transaction.atomic():
            balance_after = get_or_create_current_wallet(user=user).available_credits
            charged = 0
            if credits_enabled:
                consumption = consume_account_credit_reservation(
                    user=user,
                    credits=credits,
                    reference_type=REFERENCE_TYPE,
                    reference_id=reference_id,
                    reason="nutrition_label_scan_completed",
                    metadata={
                        "analysis_id": str(analysis.public_id),
                        "escalated": escalated,
                        "fixed_scan_price": credits,
                    },
                )
                if not consumption.get("consumed"):
                    raise RuntimeError("credit_consumption_failed")
                charged = credits
                balance_after = int(consumption.get("balance_after") or 0)
            result = {
                "analysis_id": str(analysis.public_id),
                **selected,
                "ocr_engine": "openai_responses",
                "ocr_engine_version": "nutrition_label_ai.v1",
                "credits_charged": charged,
                "available_credits": balance_after,
            }
            analysis.status = FoodLabelAIAnalysis.STATUS_COMPLETED
            analysis.result_payload = result
            analysis.final_model = selected_call.model
            analysis.escalated = escalated
            analysis.escalation_reason = str(escalation_reason or "")[:120]
            analysis.provider_call_count = len(calls)
            analysis.credits_charged = charged
            analysis.estimated_cost_usd = total_cost
            analysis.error_type = ""
            analysis.completed_at = timezone.now()
            analysis.save(
                update_fields=[
                    "status",
                    "result_payload",
                    "final_model",
                    "escalated",
                    "escalation_reason",
                    "provider_call_count",
                    "credits_charged",
                    "estimated_cost_usd",
                    "error_type",
                    "completed_at",
                    "updated_at",
                ]
            )
            if usage_events and charged:
                selected_index = next(
                    (index for index, call in enumerate(calls) if call.stage == selected_stage),
                    len(usage_events) - 1,
                )
                event = usage_events[min(selected_index, len(usage_events) - 1)]
                event.charged_credits = credits
                event.credit_plan_code = get_or_create_current_wallet(user=user).plan_snapshot_code
                event.save(update_fields=["charged_credits", "credit_plan_code"])
    except Exception as exc:
        _release_if_needed(
            user=user,
            enabled=credits_enabled,
            reference_id=reference_id,
            reason="credit_consumption_failed",
        )
        _fail_analysis(
            analysis,
            "credit_consumption_failed",
            calls=calls,
            escalated=escalated,
            escalation_reason=escalation_reason,
        )
        raise NutritionLabelAIError(
            "nutrition_label_credit_charge_failed",
            "No pudimos confirmar el cobro de la digitalización. No se creó ningún alimento.",
            503,
        ) from exc
    return result


def _reserve_scan_credits(
    *, user, analysis: FoodLabelAIAnalysis, credits: int, enabled: bool, reference_id: str
) -> None:
    if not enabled:
        return
    try:
        reserve_account_credits(
            user=user,
            credits=credits,
            reference_type=REFERENCE_TYPE,
            reference_id=reference_id,
            reason="nutrition_label_scan_reservation",
            metadata={"analysis_id": str(analysis.public_id), "fixed_scan_price": credits},
        )
    except (InsufficientAccountCredits, AccountCreditsFrozen) as exc:
        _fail_analysis(analysis, "insufficient_credits")
        raise NutritionLabelAIError(
            "nutrition_label_insufficient_credits",
            f"Necesitas {credits} créditos disponibles para digitalizar esta etiqueta.",
            402,
        ) from exc


def _decode_image(value: str, content_type: str) -> tuple[bytes, str]:
    clean_type = str(content_type or "").lower().strip()
    if clean_type not in ALLOWED_IMAGE_TYPES:
        raise NutritionLabelAIError("nutrition_label_image_type_invalid", "Usa una imagen JPEG, PNG o WebP.")
    encoded = str(value or "").strip()
    if "," in encoded and encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise NutritionLabelAIError("nutrition_label_image_invalid", "La imagen no pudo ser procesada.") from exc
    max_bytes = max(100_000, int(getattr(settings, "NUTRITION_LABEL_AI_MAX_IMAGE_BYTES", 1_500_000)))
    if len(decoded) < 10_000 or len(decoded) > max_bytes:
        raise NutritionLabelAIError(
            "nutrition_label_image_size_invalid",
            "La imagen es demasiado pequeña o supera el tamaño permitido.",
        )
    signatures = {
        "image/jpeg": decoded.startswith(b"\xff\xd8\xff"),
        "image/png": decoded.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/webp": decoded.startswith(b"RIFF") and decoded[8:12] == b"WEBP",
    }
    if not signatures[clean_type]:
        raise NutritionLabelAIError("nutrition_label_image_invalid", "La imagen no pudo ser procesada.")
    return decoded, clean_type


def _start_analysis(*, user, idempotency_key: str, request_hash: str, image_sha: str):
    with transaction.atomic():
        existing = (
            FoodLabelAIAnalysis.objects.select_for_update().filter(user=user, idempotency_key=idempotency_key).first()
        )
        if existing:
            if existing.request_hash != request_hash:
                raise NutritionLabelAIError(
                    "nutrition_label_ai_idempotency_conflict",
                    "Esta solicitud ya fue usada para otra imagen.",
                    409,
                )
            if existing.status == FoodLabelAIAnalysis.STATUS_COMPLETED:
                return existing, True
            if existing.status == FoodLabelAIAnalysis.STATUS_PROCESSING:
                if existing.updated_at >= timezone.now() - timedelta(minutes=2):
                    raise NutritionLabelAIError(
                        "nutrition_label_ai_already_processing",
                        "Esta etiqueta ya se está procesando.",
                        409,
                    )
                release_account_credit_reservation(
                    user=user,
                    reference_type=REFERENCE_TYPE,
                    reference_id=f"{existing.public_id}:{existing.attempt_count}",
                    reason="nutrition_label_scan_stale_retry",
                )
            existing.status = FoodLabelAIAnalysis.STATUS_PROCESSING
            existing.error_type = ""
            existing.attempt_count += 1
            existing.save(update_fields=["status", "error_type", "attempt_count", "updated_at"])
            return existing, False
        return FoodLabelAIAnalysis.objects.create(
            user=user,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            image_sha256=image_sha,
        ), False


def _try_provider(*, image_bytes: bytes, content_type: str, model: str, stage: str, calls: list[ProviderCall]):
    started = time.monotonic()
    try:
        data = _call_openai(image_bytes=image_bytes, content_type=content_type, model=model)
    except Exception as exc:
        safe_message = str(exc)
        error_type = (
            safe_message
            if safe_message.startswith(("openai_http_", "nutrition_label_ai_", "openai_invalid_"))
            else exc.__class__.__name__
        )
        calls.append(
            ProviderCall(
                model=model, stage=stage, elapsed_ms=int((time.monotonic() - started) * 1000), error_type=error_type
            )
        )
        return None, f"provider_{stage}_{error_type}"[:120]
    calls.append(
        ProviderCall(
            model=str(data.get("model") or model),
            stage=stage,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            data=data,
        )
    )
    try:
        return json.loads(_response_text(data)), ""
    except (TypeError, ValueError, json.JSONDecodeError):
        return None, f"provider_{stage}_invalid_json"


def _call_openai(*, image_bytes: bytes, content_type: str, model: str) -> Mapping[str, Any]:
    api_key = str(getattr(settings, "AI_ASSISTANT_OPENAI_API_KEY", "") or "").strip()
    base_url = str(getattr(settings, "AI_ASSISTANT_OPENAI_BASE_URL", "https://api.openai.com/v1") or "").rstrip("/")
    if not api_key or not model:
        raise RuntimeError("nutrition_label_ai_not_configured")
    payload = {
        "model": model,
        "store": False,
        "input": [
            {"role": "developer", "content": [{"type": "input_text", "text": LABEL_PROMPT}]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_image",
                        "image_url": f"data:{content_type};base64,{base64.b64encode(image_bytes).decode('ascii')}",
                        "detail": "high",
                    },
                    {"type": "input_text", "text": "Extract this nutrition label."},
                ],
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "nutrition_label",
                "strict": True,
                "schema": LABEL_RESPONSE_SCHEMA,
            }
        },
        "reasoning": {"effort": "low"},
        "max_output_tokens": 1000,
    }
    response = requests.post(
        f"{base_url}/responses",
        json=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=max(5, int(getattr(settings, "NUTRITION_LABEL_AI_TIMEOUT_SECONDS", 30))),
    )
    if response.status_code >= 400:
        raise RuntimeError(f"openai_http_{response.status_code}")
    data = response.json()
    if not isinstance(data, Mapping):
        raise RuntimeError("openai_invalid_response")
    return data


def _response_text(data: Mapping[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    for item in data.get("output") or []:
        if not isinstance(item, Mapping):
            continue
        for content in item.get("content") or []:
            if isinstance(content, Mapping) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text.strip()
    raise ValueError("missing_output_text")


def _normalize_provider_payload(payload: Any) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(payload, Mapping):
        return None, "invalid_output"
    if payload.get("status") != "resolved":
        return None, str(payload.get("status") or "invalid_output")[:120]
    basis = str(payload.get("basis") or "")
    if basis not in {"per_100g", "per_serving"}:
        return None, "unsupported_or_unknown_basis"
    serving_size = _number(payload.get("serving_size_g"), maximum=10_000)
    if basis == "per_serving" and (serving_size is None or serving_size <= 0):
        return None, "serving_size_required"
    source_values = {
        "energy_kcal": _energy_kcal(payload.get("energy_value"), payload.get("energy_unit")),
        "protein_g": _number(payload.get("protein_g"), maximum=10_000),
        "carbs_g": _number(payload.get("carbs_g"), maximum=10_000),
        "fat_g": _number(payload.get("fat_g"), maximum=10_000),
        "saturated_fat_g": _number(payload.get("saturated_fat_g"), maximum=10_000),
        "sugar_g": _number(payload.get("sugar_g"), maximum=10_000),
        "fiber_g": _number(payload.get("fiber_g"), maximum=10_000),
        "sodium_mg": _sodium_mg(payload.get("sodium_value"), payload.get("sodium_unit")),
    }
    if any(source_values[key] is None for key in ("protein_g", "carbs_g", "fat_g")):
        return None, "core_macros_missing"
    factor = 100 / serving_size if basis == "per_serving" and serving_size else 1
    values = {key: round(value * factor, 3) for key, value in source_values.items() if value is not None}
    if any(values[key] > 100 for key in ("protein_g", "carbs_g", "fat_g")):
        return None, "macro_outside_range"
    for key in ("saturated_fat_g", "sugar_g", "fiber_g"):
        if values.get(key, 0) > 100:
            values.pop(key, None)
    if values.get("energy_kcal", 0) > 10_000 or values.get("sodium_mg", 0) > 100_000:
        return None, "nutrient_outside_range"
    confidence = _number(payload.get("confidence"), maximum=1) or 0
    warnings: list[str] = []
    if basis == "per_serving":
        warnings.append("basis_normalized_from_serving")
    macro_kcal = values["protein_g"] * 4 + values["carbs_g"] * 4 + values["fat_g"] * 9
    declared = values.get("energy_kcal")
    if declared is not None and abs(declared - macro_kcal) > max(40, declared * 0.2):
        warnings.append("energy_macro_mismatch")
    return {
        "name": str(payload.get("product_name") or "").strip()[:100],
        "basis": "per_100g",
        "source_basis": basis,
        "serving_size_g": serving_size,
        "source_values": {key: value for key, value in source_values.items() if value is not None},
        "values": values,
        "field_confidence": {key: round(confidence, 3) for key in values},
        "warnings": warnings,
        "normalization_status": "ready",
        "quality_confidence": round(confidence, 3),
    }, ""


def _escalation_reason(candidate: Mapping[str, Any], local_candidate: Mapping[str, Any]) -> str:
    if float(candidate.get("quality_confidence") or 0) < 0.82:
        return "primary_low_confidence"
    if "energy_macro_mismatch" in candidate.get("warnings", []):
        return "primary_energy_mismatch"
    ai_values = candidate.get("values") if isinstance(candidate.get("values"), Mapping) else {}
    local_values = local_candidate.get("values") if isinstance(local_candidate.get("values"), Mapping) else {}
    disagreements = 0
    for key in ("protein_g", "carbs_g", "fat_g"):
        ai_value = _number(ai_values.get(key), maximum=100)
        local_value = _number(local_values.get(key), maximum=100)
        if ai_value is None or local_value is None:
            continue
        if abs(ai_value - local_value) > max(1.5, max(ai_value, local_value) * 0.2):
            disagreements += 1
    return "local_candidate_disagreement" if disagreements >= 2 else ""


def _safe_local_candidate(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    raw_values = value.get("values") if isinstance(value.get("values"), Mapping) else {}
    values = {}
    for key in ("energy_kcal", "protein_g", "carbs_g", "fat_g", "saturated_fat_g", "sugar_g", "fiber_g", "sodium_mg"):
        number = _number(raw_values.get(key), maximum=100_000)
        if number is not None:
            values[key] = number
    return {"basis": str(value.get("basis") or "")[:24], "values": values}


def _number(value: Any, *, maximum: float) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and 0 <= number <= maximum else None


def _energy_kcal(value: Any, unit: Any) -> float | None:
    number = _number(value, maximum=50_000)
    if number is None:
        return None
    return number / 4.184 if unit == "kJ" else number if unit == "kcal" else None


def _sodium_mg(value: Any, unit: Any) -> float | None:
    number = _number(value, maximum=100_000)
    if number is None:
        return None
    return number * 1000 if unit == "g" else number if unit == "mg" else None


def _safe_int(value: Any) -> int | None:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _record_calls(
    *, user, analysis: FoodLabelAIAnalysis, calls: list[ProviderCall], selected_stage: str
) -> list[AIUsageEvent]:
    if not getattr(settings, "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED", True):
        return []
    events = []
    for call in calls:
        usage = call.usage
        input_tokens = _safe_int(usage.get("input_tokens"))
        output_tokens = _safe_int(usage.get("output_tokens"))
        total_tokens = _safe_int(usage.get("total_tokens"))
        details = usage.get("input_tokens_details")
        cached = _safe_int(details.get("cached_tokens")) if isinstance(details, Mapping) else None
        events.append(
            AIUsageEvent.objects.create(
                user=user,
                period=timezone.localdate().strftime("%Y-%m"),
                turn_id=str(analysis.public_id),
                action_type=ACTION_TYPE,
                provider="openai",
                model_name=call.model,
                input_tokens=input_tokens,
                cached_input_tokens=cached,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=call.estimated_cost_usd,
                status=AIUsageEvent.Status.ERROR if call.error_type else AIUsageEvent.Status.COMPLETED,
                error_type=call.error_type,
                latency_ms=call.elapsed_ms,
                usage_payload={"provider_usage": dict(usage)},
                metadata={
                    "surface": "mobile_label_capture",
                    "stage": call.stage,
                    "selected": call.stage == selected_stage,
                    "analysis_id": str(analysis.public_id),
                },
            )
        )
    return events


def _release_if_needed(*, user, enabled: bool, reference_id: str, reason: str) -> None:
    if enabled:
        release_account_credit_reservation(
            user=user,
            reference_type=REFERENCE_TYPE,
            reference_id=reference_id,
            reason="nutrition_label_scan_failed",
            metadata={"error_type": str(reason)[:120]},
        )


def _fail_analysis(
    analysis: FoodLabelAIAnalysis,
    error_type: str,
    *,
    calls: list[ProviderCall] | None = None,
    escalated: bool = False,
    escalation_reason: str = "",
) -> None:
    calls = calls or []
    analysis.status = FoodLabelAIAnalysis.STATUS_FAILED
    analysis.error_type = str(error_type or "unknown")[:120]
    analysis.escalated = escalated
    analysis.escalation_reason = str(escalation_reason or "")[:120]
    analysis.provider_call_count = len(calls)
    analysis.estimated_cost_usd = sum((call.estimated_cost_usd or Decimal("0")) for call in calls)
    analysis.completed_at = timezone.now()
    analysis.save(
        update_fields=[
            "status",
            "error_type",
            "escalated",
            "escalation_reason",
            "provider_call_count",
            "estimated_cost_usd",
            "completed_at",
            "updated_at",
        ]
    )
