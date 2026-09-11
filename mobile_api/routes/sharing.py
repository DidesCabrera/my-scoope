from __future__ import annotations

from uuid import UUID

from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.sharing import ShareResourceCreateInput, ShareResourceEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.application.sharing.dailyplans import DailyPlanShareError, create_dailyplan_share_resource
from notas.application.sharing.services import ShareUnavailable, revoke_share_resource
from notas.domain.models import ShareResource

router = Router()


def _resource_payload(request, resource: ShareResource) -> dict:
    relative_url = f"/s/{resource.public_id}"
    return {
        "id": resource.public_id,
        "subject_type": resource.subject_type,
        "title": resource.snapshot["subject"]["title"],
        "public_url": request.build_absolute_uri(relative_url),
        "claim_policy": resource.claim_policy,
        "status": resource.status,
        "created_at": resource.created_at,
    }


@router.post(
    "/shares/daily-plans/{dailyplan_id}",
    operation_id="mobile_api_create_dailyplan_share_resource",
    auth=mobile_bearer,
    response={200: ShareResourceEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def create_dailyplan_share(request, dailyplan_id: int, payload: ShareResourceCreateInput):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    try:
        result = create_dailyplan_share_resource(
            sender=request.auth.user,
            dailyplan_id=dailyplan_id,
            claim_policy=payload.claim_policy,
        )
    except DailyPlanShareError as exc:
        raise MobileAPIError(str(exc), "El plan no está disponible para compartir.", 404) from exc
    return success(_resource_payload(request, result.resource))


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
