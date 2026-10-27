from accounts.services.profile import build_account_credit_display
from notas.application.services.notifications.center import unread_notification_count
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import (
    InboxItem,
)


def user_weight(request):
    if request.user.is_authenticated:
        user = request.user
        current_weight = get_current_weight(user)
        return {
            "sidebar_credits": build_account_credit_display(user),
            "current_weight": current_weight,
            "current_weight_label": f"{float(current_weight):.1f}".replace(".", ",") if current_weight is not None else "",
            "notification_unread_count": unread_notification_count(user),
        }

    return {
        "sidebar_credits": None,
        "current_weight": None,
        "current_weight_label": "",
        "notification_unread_count": 0,
    }


def shared_count(request):
    if request.user.is_authenticated:
        return {
            "shared_count": InboxItem.objects.filter(
                owner=request.user,
                dismissed_at__isnull=True,
            ).count()
        }
    return {}
