from django.db.models import Q

from accounts.services.profile import build_account_credit_display
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import (
    InboxItem,
    NutritionProposal,
)


def user_weight(request):
    if request.user.is_authenticated:
        user = request.user
        current_weight = get_current_weight(user)
        inbox_unread_count = InboxItem.objects.filter(
            owner=user,
            dismissed_at__isnull=True,
            read_at__isnull=True,
        ).count()
        proposal_unread_count = (
            NutritionProposal.objects.filter(
                Q(created_by=user) | Q(dailyplan__created_by=user),
                is_read=False,
            )
            .distinct()
            .count()
        )

        inbox_seen_count = int(request.session.get("inbox_notification_seen_count", 0) or 0)
        proposal_seen_count = int(request.session.get("proposal_notification_seen_count", 0) or 0)

        return {
            "sidebar_credits": build_account_credit_display(user),
            "current_weight": current_weight,
            "current_weight_label": f"{float(current_weight):.1f}".replace(".", ",") if current_weight is not None else "",
            "inbox_unread_count": inbox_unread_count,
            "proposal_unread_count": proposal_unread_count,
            "inbox_notification_seen": bool(inbox_unread_count and inbox_unread_count <= inbox_seen_count),
            "proposal_notification_seen": bool(proposal_unread_count and proposal_unread_count <= proposal_seen_count),
        }

    return {
        "sidebar_credits": None,
        "current_weight": None,
        "current_weight_label": "",
        "inbox_unread_count": 0,
        "proposal_unread_count": 0,
        "inbox_notification_seen": False,
        "proposal_notification_seen": False,
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
