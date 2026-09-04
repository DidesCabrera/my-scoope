import json
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Avg, Sum
from django.utils import timezone

from notas.domain.models import FoodLabelAIAnalysis


class Command(BaseCommand):
    help = "Report resolution, hidden escalation and internal cost metrics for AI nutrition-label scans."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        days = max(1, min(int(options["days"]), 3650))
        since = timezone.now() - timedelta(days=days)
        scans = FoodLabelAIAnalysis.objects.filter(created_at__gte=since)
        completed = scans.filter(status=FoodLabelAIAnalysis.STATUS_COMPLETED)
        failed = scans.filter(status=FoodLabelAIAnalysis.STATUS_FAILED)
        escalated = scans.filter(escalated=True)
        total = scans.count()
        cost = scans.aggregate(total=Sum("estimated_cost_usd"), average=Avg("estimated_cost_usd"))
        payload = {
            "window_days": days,
            "total_scans": total,
            "completed_scans": completed.count(),
            "failed_scans": failed.count(),
            "resolution_rate_percent": round(completed.count() * 100 / total, 2) if total else 0,
            "escalated_scans": escalated.count(),
            "escalation_rate_percent": round(escalated.count() * 100 / total, 2) if total else 0,
            "credits_charged": int(completed.aggregate(total=Sum("credits_charged"))["total"] or 0),
            "estimated_provider_cost_usd": _money(cost["total"]),
            "average_provider_cost_usd": _money(cost["average"]),
        }
        self.stdout.write(json.dumps(payload, sort_keys=True))


def _money(value) -> str:
    return str((value or Decimal("0")).quantize(Decimal("0.000001")))
