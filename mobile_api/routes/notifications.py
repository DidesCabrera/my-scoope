from ninja import Router

from mobile_api.api_support import require_scope, success
from mobile_api.auth import mobile_bearer
from mobile_api.errors import MobileAPIError
from mobile_api.schema_domains.notifications import NotificationListEnvelope
from mobile_api.schemas import ErrorEnvelope
from notas.application.services.notifications.center import list_notifications, mark_all_notifications_read, mark_notification_read, unread_notification_count
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_WRITE
from notas.presentation.notifications import present_notifications

router = Router(auth=mobile_bearer)


def _feed(request):
    items = present_notifications(list_notifications(request.auth.user))
    for item in items:
        item["web_url"] = request.build_absolute_uri(item["web_url"])
    return {"items": items, "unread_count": unread_notification_count(request.auth.user)}


@router.get(
    "/notifications",
    operation_id="mobile_api_notifications",
    response={200: NotificationListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def notifications(request):
    return success(_feed(request))


@router.post(
    "/notifications/read-all",
    operation_id="mobile_api_mark_all_notifications_read",
    response={200: NotificationListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope},
)
def notification_read_all(request):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    mark_all_notifications_read(request.auth.user)
    return success(_feed(request))


@router.post(
    "/notifications/{kind}/{item_id}/read",
    operation_id="mobile_api_mark_notification_read",
    response={200: NotificationListEnvelope, 401: ErrorEnvelope, 403: ErrorEnvelope, 404: ErrorEnvelope},
)
def notification_read(request, kind: str, item_id: int):
    require_scope(request.auth, MOBILE_SCOPE_WRITE)
    if not mark_notification_read(request.auth.user, kind, item_id):
        raise MobileAPIError("notification_not_found", "La notificación no existe.", 404)
    return success(_feed(request))
