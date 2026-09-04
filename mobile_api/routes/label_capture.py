from __future__ import annotations

import base64

from ninja import Router

from accounts.services.credits import get_or_create_current_wallet
from core.rate_limits import is_nutrition_label_scan_rate_limited
from mobile_api.api_support import food_label_error, require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.label_capture import (
    FoodLabelAIAnalysisEnvelope,
    FoodLabelAIAnalysisInput,
    FoodLabelAIConfigEnvelope,
    FoodLabelCaptureEnvelope,
    FoodLabelCaptureInput,
    FoodLabelImageDeleteEnvelope,
    FoodLabelImageEnvelope,
)
from mobile_api.schemas import ErrorEnvelope
from mobile_api.selectors import food_label_capture_payload
from notas.application.services.access.capabilities import get_capabilities
from notas.application.services.commands.food_commands import create_food_from_label_capture
from notas.application.services.nutrition_label_ai import (
    NutritionLabelAIError,
    analyze_nutrition_label,
    nutrition_label_scan_cost,
    validate_retained_label_image,
)
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.domain.models import FoodLabelCaptureReceipt

router = Router()


@router.get(
    "/foods/label-captures/config",
    operation_id="mobile_api_api_food_label_capture_config",
    auth=mobile_bearer,
    response={200: FoodLabelAIConfigEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def food_label_capture_config(request):
    capabilities = get_capabilities(request.auth.user)
    wallet = get_or_create_current_wallet(user=request.auth.user)
    cost = nutrition_label_scan_cost()
    can_create = capabilities is not None and capabilities.can_create_food()
    return success(
        {
            "credits_per_scan": cost,
            "available_credits": wallet.available_credits,
            "can_scan": bool(can_create and wallet.available_credits >= cost),
            "image_retention_available": True,
        }
    )


@router.post(
    "/foods/label-captures/analyze",
    operation_id="mobile_api_api_analyze_food_label_capture",
    auth=mobile_bearer,
    response={
        200: FoodLabelAIAnalysisEnvelope,
        402: ErrorEnvelope,
        403: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        429: ErrorEnvelope,
        503: ErrorEnvelope,
    },
)
def analyze_food_label_capture(request, payload: FoodLabelAIAnalysisInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    capabilities = get_capabilities(request.auth.user)
    if capabilities is None or not capabilities.can_create_food():
        raise MobileAPIError("food_creation_not_entitled", "The current account cannot create private foods.", 403)
    if is_nutrition_label_scan_rate_limited(request):
        raise MobileAPIError(
            "nutrition_label_scan_rate_limited",
            "Se alcanzó el límite temporal de digitalizaciones. Inténtalo más tarde.",
            429,
        )
    try:
        result = analyze_nutrition_label(
            user=request.auth.user,
            image_base64=payload.image_base64,
            image_content_type=payload.image_content_type,
            image_width=payload.image_width,
            image_height=payload.image_height,
            idempotency_key=payload.idempotency_key,
            consent_to_ai_processing=payload.consent_to_ai_processing,
            local_candidate=payload.local_candidate.model_dump() if payload.local_candidate else None,
        )
    except NutritionLabelAIError as exc:
        raise MobileAPIError(exc.code, exc.message, exc.status_code) from exc
    return success(result)


@router.post(
    "/foods/label-captures",
    operation_id="mobile_api_api_confirm_food_label_capture",
    auth=mobile_bearer,
    response={
        200: FoodLabelCaptureEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        422: ErrorEnvelope,
        503: ErrorEnvelope,
    },
)
def confirm_food_label_capture(request, payload: FoodLabelCaptureInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    capabilities = get_capabilities(request.auth.user)
    if capabilities is None or not capabilities.can_create_food():
        raise MobileAPIError(
            code="food_creation_not_entitled",
            message="The current account cannot create private foods.",
            status_code=403,
        )
    retained_image = None
    retained_content_type = ""
    retained_sha256 = ""
    try:
        if payload.retain_label_image:
            if not payload.analysis_id or not payload.label_image_base64 or not payload.label_image_content_type:
                raise NutritionLabelAIError(
                    "nutrition_label_retained_image_required",
                    "Falta la imagen procesada que elegiste guardar.",
                )
            retained_image, retained_content_type, retained_sha256 = validate_retained_label_image(
                user=request.auth.user,
                analysis_id=payload.analysis_id,
                image_base64=payload.label_image_base64,
                image_content_type=payload.label_image_content_type,
            )
        result = create_food_from_label_capture(
            user=request.auth.user,
            name=payload.name,
            protein_g=payload.protein_g,
            carbs_g=payload.carbs_g,
            fat_g=payload.fat_g,
            saturated_fat_g=payload.saturated_fat_g,
            sugar_g=payload.sugar_g,
            fiber_g=payload.fiber_g,
            sodium_mg=payload.sodium_mg,
            serving_size_g=payload.serving_size_g,
            declared_energy_kcal_per_100g=payload.declared_energy_kcal_per_100g,
            detected_basis=payload.detected_basis,
            ocr_engine=payload.ocr_engine,
            ocr_engine_version=payload.ocr_engine_version,
            field_confidence=payload.field_confidence,
            warnings=payload.warnings,
            idempotency_key=payload.idempotency_key,
            retained_label_image=retained_image,
            retained_label_image_content_type=retained_content_type,
            retained_label_image_sha256=retained_sha256,
        )
    except NutritionLabelAIError as exc:
        raise MobileAPIError(exc.code, exc.message, exc.status_code) from exc
    except ValueError as exc:
        raise food_label_error(exc) from exc
    return success(food_label_capture_payload(result))


def _owned_label_receipt(user, receipt_id: int) -> FoodLabelCaptureReceipt:
    receipt = (
        FoodLabelCaptureReceipt.objects.select_related("food")
        .filter(
            pk=receipt_id,
            food__created_by=user,
            food__is_active=True,
        )
        .first()
    )
    if receipt is None:
        raise MobileAPIError("nutrition_label_image_not_found", "La imagen guardada no está disponible.", 404)
    return receipt


@router.get(
    "/foods/label-captures/{receipt_id}/image",
    operation_id="mobile_api_api_food_label_capture_image",
    auth=mobile_bearer,
    response={200: FoodLabelImageEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def food_label_capture_image(request, receipt_id: int):
    receipt = _owned_label_receipt(request.auth.user, receipt_id)
    if not receipt.retained_label_image:
        raise MobileAPIError("nutrition_label_image_not_found", "La imagen guardada no está disponible.", 404)
    return success(
        {
            "receipt_id": receipt.id,
            "content_type": receipt.retained_label_image_content_type,
            "image_base64": base64.b64encode(bytes(receipt.retained_label_image)).decode("ascii"),
            "size_bytes": receipt.retained_label_image_size,
        }
    )


@router.delete(
    "/foods/label-captures/{receipt_id}/image",
    operation_id="mobile_api_api_delete_food_label_capture_image",
    auth=mobile_bearer,
    response={200: FoodLabelImageDeleteEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def delete_food_label_capture_image(request, receipt_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    receipt = _owned_label_receipt(request.auth.user, receipt_id)
    deleted = bool(receipt.retained_label_image)
    receipt.retained_label_image = None
    receipt.retained_label_image_content_type = ""
    receipt.retained_label_image_sha256 = ""
    receipt.retained_label_image_size = 0
    receipt.save(
        update_fields=[
            "retained_label_image",
            "retained_label_image_content_type",
            "retained_label_image_sha256",
            "retained_label_image_size",
        ]
    )
    return success({"receipt_id": receipt.id, "deleted": deleted})
