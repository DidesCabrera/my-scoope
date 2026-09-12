from __future__ import annotations

from uuid import UUID

from ninja import Router

from core.rate_limits import (
    is_sharing_claim_rate_limited,
    is_sharing_create_rate_limited,
    is_sharing_preview_rate_limited,
)
from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.sharing import (
    PublicShareResourceEnvelope,
    ShareClaimEnvelope,
    ShareResourceCreateInput,
    ShareResourceEnvelope,
    SharingInboxEnvelope,
    SharingInboxItemEnvelope,
    SharingInboxSaveEnvelope,
    SharingInboxUpdateInput,
)
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.application.sharing.dailyplans import DailyPlanShareError, create_dailyplan_share_resource
from notas.application.sharing.inbox import save_dailyplan_inbox_item, update_inbox_item
from notas.application.sharing.services import (
    ShareUnavailable,
    claim_share_resource,
    get_share_resource_for_preview,
    record_share_preview,
    revoke_share_resource,
)
from notas.domain.models import InboxItem, ShareClaim, ShareResource

router = Router()


def _resource_payload(request, resource: ShareResource) -> dict:
    relative_url = f"/s/{resource.public_id}/"
    return {
        "id": resource.public_id,
        "subject_type": resource.subject_type,
        "title": resource.snapshot["subject"]["title"],
        "public_url": request.build_absolute_uri(relative_url),
        "claim_policy": resource.claim_policy,
        "status": resource.status,
        "created_at": resource.created_at,
    }


def _inbox_item_payload(request, item: InboxItem) -> dict:
    resource = item.resource
    return {
        "id": item.id,
        "resource_id": resource.public_id,
        "subject_type": resource.subject_type,
        "title": (resource.snapshot.get("subject") or {}).get("title") or "Contenido compartido",
        "sender": resource.sender.get_full_name() or resource.sender.username,
        "public_url": request.build_absolute_uri(f"/s/{resource.public_id}/"),
        "is_read": item.read_at is not None,
        "is_favorite": item.is_favorite,
        "is_saved": item.saved_at is not None,
        "created_at": item.created_at,
    }


def _owned_inbox_item(user, item_id: int) -> InboxItem:
    item = InboxItem.objects.filter(pk=item_id, owner=user).select_related("resource", "resource__sender").first()
    if item is None:
        raise MobileAPIError("sharing_inbox_item_not_found", "El elemento de Inbox no existe.", 404)
    return item


@router.post(
    "/shares/daily-plans/{dailyplan_id}",
    operation_id="mobile_api_create_dailyplan_share_resource",
    auth=mobile_bearer,
    response={
        200: ShareResourceEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        429: ErrorEnvelope,
    },
)
def create_dailyplan_share(request, dailyplan_id: int, payload: ShareResourceCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if is_sharing_create_rate_limited(request):
        raise MobileAPIError("sharing_create_rate_limited", "Inténtalo nuevamente más tarde.", 429)
    try:
        result = create_dailyplan_share_resource(
            sender=request.auth.user,
            dailyplan_id=dailyplan_id,
            claim_policy=payload.claim_policy,
        )
    except DailyPlanShareError as exc:
        raise MobileAPIError(str(exc), "El plan no está disponible para compartir.", 404) from exc
    return success(_resource_payload(request, result.resource))


@router.get(
    "/shares/inbox",
    operation_id="mobile_api_sharing_inbox",
    auth=mobile_bearer,
    response={200: SharingInboxEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def sharing_inbox(request):
    items = list(
        InboxItem.objects.filter(owner=request.auth.user, dismissed_at__isnull=True)
        .select_related("resource", "resource__sender")
        .order_by("-created_at", "-id")
    )
    return success({"items": [_inbox_item_payload(request, item) for item in items], "count": len(items)})


@router.patch(
    "/shares/inbox/{item_id}",
    operation_id="mobile_api_update_sharing_inbox_item",
    auth=mobile_bearer,
    response={200: SharingInboxItemEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def update_sharing_inbox_item(request, item_id: int, payload: SharingInboxUpdateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item = _owned_inbox_item(request.auth.user, item_id)
    updated = update_inbox_item(
        inbox_item=item,
        actor=request.auth.user,
        is_read=payload.is_read,
        is_favorite=payload.is_favorite,
        dismissed=payload.dismissed,
    )
    updated.resource = item.resource
    return success(_inbox_item_payload(request, updated))


@router.post(
    "/shares/inbox/{item_id}/save",
    operation_id="mobile_api_save_sharing_inbox_item",
    auth=mobile_bearer,
    response={200: SharingInboxSaveEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope, 422: ErrorEnvelope},
)
def save_sharing_inbox_item(request, item_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    item = _owned_inbox_item(request.auth.user, item_id)
    try:
        saved = save_dailyplan_inbox_item(inbox_item=item, actor=request.auth.user)
    except ShareUnavailable as exc:
        raise MobileAPIError(str(exc), "El contenido compartido no se puede guardar.", 422) from exc
    return success({"entity": "dailyPlan", "item_id": saved.id})


@router.get(
    "/shares/{public_id}",
    operation_id="mobile_api_public_share_resource",
    auth=None,
    response={200: PublicShareResourceEnvelope, 404: ErrorEnvelope, 429: ErrorEnvelope},
)
def public_share_resource(request, public_id: UUID):
    if is_sharing_preview_rate_limited(request):
        raise MobileAPIError("sharing_preview_rate_limited", "Inténtalo nuevamente más tarde.", 429)
    try:
        resource = get_share_resource_for_preview(public_id=public_id)
    except ShareUnavailable as exc:
        raise MobileAPIError(str(exc), "El contenido compartido no está disponible.", 404) from exc
    record_share_preview(resource=resource)
    return success(
        {
            "id": resource.public_id,
            "subject_type": resource.subject_type,
            "title": (resource.snapshot.get("subject") or {}).get("title") or "Contenido compartido",
            "claim_policy": resource.claim_policy,
            "snapshot": resource.snapshot,
        }
    )


@router.post(
    "/shares/{public_id}/claims",
    operation_id="mobile_api_claim_share_resource",
    auth=mobile_bearer,
    response={
        200: ShareClaimEnvelope,
        401: ErrorEnvelope,
        403: ErrorEnvelope,
        404: ErrorEnvelope,
        409: ErrorEnvelope,
        429: ErrorEnvelope,
    },
)
def claim_share(request, public_id: UUID):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if is_sharing_claim_rate_limited(request):
        raise MobileAPIError("sharing_claim_rate_limited", "Inténtalo nuevamente más tarde.", 429)
    try:
        resource = get_share_resource_for_preview(public_id=public_id)
        _, inbox_item = claim_share_resource(
            resource=resource,
            user=request.auth.user,
            source=ShareClaim.Source.LINK,
        )
    except ShareUnavailable as exc:
        code = str(exc)
        status = 404 if code in {"share_resource_not_found", "share_resource_not_active", "share_resource_expired"} else 409
        raise MobileAPIError(code, "El contenido compartido no se puede agregar.", status) from exc
    return success({"resource_id": resource.public_id, "inbox_item_id": inbox_item.id})


@router.delete(
    "/shares/{public_id}",
    operation_id="mobile_api_revoke_share_resource",
    auth=mobile_bearer,
    response={200: ShareResourceEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def revoke_share(request, public_id: UUID):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    resource = ShareResource.objects.filter(public_id=public_id).first()
    if resource is None:
        raise MobileAPIError("share_resource_not_found", "El recurso compartido no existe.", 404)
    try:
        revoked = revoke_share_resource(resource=resource, actor=request.auth.user)
    except ShareUnavailable as exc:
        raise MobileAPIError(str(exc), "El recurso compartido no está disponible.", 404) from exc
    return success(_resource_payload(request, revoked))
