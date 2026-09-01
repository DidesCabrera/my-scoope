from __future__ import annotations

from typing import Any

from ninja import Router

from mobile_api.api_support import (
    comparison_error,
    require_scope,
    success,
)
from mobile_api.auth import mobile_bearer
from mobile_api.comparisons import (
    comparison_metadata_payload,
    comparison_options_payload,
    dynamic_comparison_payload,
    save_comparison,
    saved_comparison_detail_payload,
    saved_comparison_list_payload,
    update_comparison,
)
from mobile_api.schema_domains.comparisons import (
    ComparisonMetadataEnvelope,
    ComparisonRequestInput,
    ComparisonResultEnvelope,
    SavedComparisonDetailEnvelope,
    SavedComparisonListEnvelope,
)
from mobile_api.schemas import ComparisonOptionsEnvelope, ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE

router = Router(auth=mobile_bearer)


def _comparison_selections(payload: ComparisonRequestInput) -> list[dict[str, float | int | None]]:
    return [{"id": selection.id, "quantity": selection.quantity} for selection in payload.selections]


@router.get(
    "/comparisons/metadata",
    response={200: ComparisonMetadataEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
    operation_id="mobile_api_api_comparison_metadata",
)
def comparison_metadata(request: Any) -> dict[str, Any]:
    return success(comparison_metadata_payload())


@router.get(
    "/comparisons/options/{kind}",
    response={200: ComparisonOptionsEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_comparison_options",
)
def comparison_options(
    request: Any,
    kind: str,
    search: str | None = None,
    offset: int = 0,
    limit: int = 30,
) -> dict[str, Any]:
    try:
        payload = comparison_options_payload(
            request.auth.user,
            kind=kind,
            search=search,
            offset=offset,
            limit=limit,
        )
    except ValueError as exc:
        raise comparison_error(exc) from exc
    return success(payload)


@router.post(
    "/comparisons/compare",
    response={200: ComparisonResultEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_compare_entities",
)
def compare_entities(request: Any, payload: ComparisonRequestInput) -> dict[str, Any]:
    try:
        result = dynamic_comparison_payload(
            request.auth.user,
            kind=payload.kind,
            selections=_comparison_selections(payload),
        )
    except ValueError as exc:
        raise comparison_error(exc) from exc
    return success(result)


@router.get(
    "/comparisons/saved",
    response={200: SavedComparisonListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_saved_comparisons",
)
def saved_comparisons(
    request: Any,
    kind: str | None = None,
    offset: int = 0,
    limit: int = 30,
) -> dict[str, Any]:
    try:
        payload = saved_comparison_list_payload(
            request.auth.user,
            kind=kind,
            offset=offset,
            limit=limit,
        )
    except ValueError as exc:
        raise comparison_error(exc) from exc
    return success(payload)


@router.post(
    "/comparisons/saved",
    response={200: SavedComparisonDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_create_mobile_saved_comparison",
)
def create_mobile_saved_comparison(request: Any, payload: ComparisonRequestInput) -> dict[str, Any]:
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        comparison = save_comparison(
            request.auth.user,
            kind=payload.kind,
            selections=_comparison_selections(payload),
        )
    except ValueError as exc:
        raise comparison_error(exc) from exc
    return success(saved_comparison_detail_payload(request.auth.user, comparison.id))


@router.get(
    "/comparisons/saved/{comparison_id}",
    response={200: SavedComparisonDetailEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
    operation_id="mobile_api_api_saved_comparison_detail",
)
def saved_comparison_detail(request: Any, comparison_id: int) -> dict[str, Any]:
    payload = saved_comparison_detail_payload(request.auth.user, comparison_id)
    if payload is None:
        raise comparison_error(ValueError("saved_comparison_not_found"))
    return success(payload)


@router.put(
    "/comparisons/saved/{comparison_id}",
    response={200: SavedComparisonDetailEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 409: ErrorEnvelope, 422: ErrorEnvelope},
    operation_id="mobile_api_api_update_mobile_saved_comparison",
)
def update_mobile_saved_comparison(
    request: Any,
    comparison_id: int,
    payload: ComparisonRequestInput,
) -> dict[str, Any]:
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        comparison = update_comparison(
            request.auth.user,
            comparison_id=comparison_id,
            kind=payload.kind,
            selections=_comparison_selections(payload),
        )
    except ValueError as exc:
        raise comparison_error(exc) from exc
    return success(saved_comparison_detail_payload(request.auth.user, comparison.id))
