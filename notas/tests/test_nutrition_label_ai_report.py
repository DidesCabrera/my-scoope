import json
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from notas.domain.models import FoodLabelAIAnalysis


class NutritionLabelAIReportTests(TestCase):
    def test_report_exposes_resolution_escalation_credits_and_internal_cost(self):
        user = User.objects.create_user(username="label-report-user")
        common = {
            "user": user,
            "request_hash": "a" * 64,
            "image_sha256": "b" * 64,
        }
        FoodLabelAIAnalysis.objects.create(
            **common,
            idempotency_key="label-report-completed",
            status=FoodLabelAIAnalysis.STATUS_COMPLETED,
            escalated=False,
            credits_charged=2,
            estimated_cost_usd="0.010000",
        )
        FoodLabelAIAnalysis.objects.create(
            **common,
            idempotency_key="label-report-failed",
            status=FoodLabelAIAnalysis.STATUS_FAILED,
            escalated=True,
            estimated_cost_usd="0.020000",
        )
        output = StringIO()

        call_command("report_nutrition_label_ai", days=30, stdout=output)

        report = json.loads(output.getvalue())
        self.assertEqual(report["total_scans"], 2)
        self.assertEqual(report["completed_scans"], 1)
        self.assertEqual(report["failed_scans"], 1)
        self.assertEqual(report["resolution_rate_percent"], 50.0)
        self.assertEqual(report["escalation_rate_percent"], 50.0)
        self.assertEqual(report["credits_charged"], 2)
        self.assertEqual(report["estimated_provider_cost_usd"], "0.030000")
