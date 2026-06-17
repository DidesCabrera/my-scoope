from django.db.models import Q

from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlanShare, MealShare, NutritionProposal


def user_weight(request):
    if request.user.is_authenticated:
        user = request.user
        inbox_unread_count = (
            DailyPlanShare.objects.filter(
                accepted_by=user,
                dismissed=False,
                removed=False,
                is_read=False,
            ).count()
            + MealShare.objects.filter(
                accepted_by=user,
                dismissed=False,
                removed=False,
                is_read=False,
            ).count()
        )
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
            "current_weight": get_current_weight(user),
            "inbox_unread_count": inbox_unread_count,
            "proposal_unread_count": proposal_unread_count,
            "inbox_notification_seen": bool(inbox_unread_count and inbox_unread_count <= inbox_seen_count),
            "proposal_notification_seen": bool(proposal_unread_count and proposal_unread_count <= proposal_seen_count),
        }

    return {
        "current_weight": None,
        "inbox_unread_count": 0,
        "proposal_unread_count": 0,
        "inbox_notification_seen": False,
        "proposal_notification_seen": False,
    }


def shared_count(request):
    if request.user.is_authenticated:
        return {
            "shared_count": DailyPlanShare.objects.filter(
                accepted_by=request.user,
                dismissed=False,
            ).count()
        }
    return {}
