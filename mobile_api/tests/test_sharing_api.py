from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, ShareResource


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPISharingTests(AuthenticatedMobileAPITestCase):
    def test_owner_can_create_and_revoke_dailyplan_share_resource(self):
        dailyplan = DailyPlan.objects.create(name="Plan desde móvil", created_by=self.user, is_draft=False)

        created = self.client.post(
            f"/api/v1/shares/daily-plans/{dailyplan.id}",
            data={"claim_policy": "multiple"},
            content_type="application/json",
        )

        self.assertEqual(created.status_code, 200)
        payload = created.json()["data"]
        self.assertEqual(payload["title"], "Plan desde móvil")
        self.assertEqual(payload["subject_type"], "daily_plan")
        self.assertEqual(payload["claim_policy"], "multiple")
        self.assertEqual(payload["status"], "active")
        self.assertEqual(payload["public_url"], f"http://testserver/s/{payload['id']}")

        revoked = self.client.delete(f"/api/v1/shares/{payload['id']}")
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(revoked.json()["data"]["status"], "revoked")
        self.assertEqual(ShareResource.objects.get(public_id=payload["id"]).status, "revoked")

    def test_user_cannot_create_or_revoke_another_users_resource(self):
        other = User.objects.create_user("mobile-share-other")
        foreign_plan = DailyPlan.objects.create(name="Plan ajeno", created_by=other, is_draft=False)
        foreign_resource = ShareResource.objects.create(
            sender=other,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            source_object_id=foreign_plan.id,
            snapshot={"subject": {"title": "Plan ajeno"}},
            snapshot_schema_version="sharing.snapshot.v1",
        )

        create_response = self.client.post(
            f"/api/v1/shares/daily-plans/{foreign_plan.id}",
            data={},
            content_type="application/json",
        )
        revoke_response = self.client.delete(f"/api/v1/shares/{foreign_resource.public_id}")

        self.assertEqual(create_response.status_code, 404)
        self.assertEqual(revoke_response.status_code, 404)
        foreign_resource.refresh_from_db()
        self.assertEqual(foreign_resource.status, ShareResource.Status.ACTIVE)
