import uuid
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notas.domain.models import CalendarizationReview, CalendarizationRevision, ProgramCalendarization


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class WebCalendarizationReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="review-web", password="secret")
        self.client.force_login(self.user)
        today = timezone.localdate()
        self.calendarization = ProgramCalendarization.objects.create(
            user=self.user, program_name_snapshot="Programa de prueba",
            start_date=today - timedelta(days=6), end_date=today + timedelta(days=7),
            timezone_name="UTC", status=ProgramCalendarization.STATUS_ACTIVE,
        )

    def test_review_records_evidence_without_changing_program(self):
        page = self.client.get(reverse("calendarization_review"))
        self.assertContains(page, "Revisión de progreso")
        self.assertContains(page, "Guardar revisión")
        response = self.client.post(reverse("calendarization_review_create"), {
            "idempotency_key": str(uuid.uuid4()),
            "energy_score": "4", "hunger_score": "2",
            "training_performance_score": "3", "note": "Buen descanso",
        })
        self.assertEqual(response.status_code, 302)
        review = CalendarizationReview.objects.get(calendarization=self.calendarization)
        self.assertEqual(review.energy_score, 4)
        self.assertEqual(review.note, "Buen descanso")
        self.assertContains(self.client.get(reverse("calendarization_review")), "Buen descanso")
        self.calendarization.refresh_from_db()
        self.assertEqual(self.calendarization.status, ProgramCalendarization.STATUS_ACTIVE)

    def test_pending_revision_can_be_rejected_only_by_owner(self):
        revision = CalendarizationRevision.objects.create(
            calendarization=self.calendarization,
            effective_from=timezone.localdate() + timedelta(days=1),
            rationale="Ajuste futuro", idempotency_key=str(uuid.uuid4()),
            before_snapshot={"days": []}, after_snapshot={"days": []},
        )
        self.assertContains(self.client.get(reverse("calendarization_review")), "Ajuste futuro")
        other = User.objects.create_user(username="other-review-web", password="secret")
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse("calendarization_revision_decide", args=[revision.id]), {
            "decision": "reject",
        }).status_code, 404)
        self.client.force_login(self.user)
        response = self.client.post(reverse("calendarization_revision_decide", args=[revision.id]), {
            "decision": "reject",
        })
        self.assertEqual(response.status_code, 302)
        revision.refresh_from_db()
        self.assertEqual(revision.status, CalendarizationRevision.STATUS_REJECTED)
