from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.sharing.dailyplans import create_dailyplan_share_resource
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
        self.assertEqual(payload["public_url"], f"http://testserver/s/{payload['id']}/")

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

    def test_public_preview_claim_and_mobile_inbox_are_one_idempotent_flow(self):
        sender = User.objects.create_user("mobile-sharing-sender", first_name="Ana")
        source = DailyPlan.objects.create(name="Plan recibido", created_by=sender, is_draft=False)
        resource = create_dailyplan_share_resource(sender=sender, dailyplan_id=source.id).resource

        public_response = Client().get(f"/api/v1/shares/{resource.public_id}")
        first_claim = self.client.post(f"/api/v1/shares/{resource.public_id}/claims")
        second_claim = self.client.post(f"/api/v1/shares/{resource.public_id}/claims")
        inbox = self.client.get("/api/v1/shares/inbox")

        self.assertEqual(public_response.status_code, 200)
        self.assertEqual(public_response.json()["data"]["title"], "Plan recibido")
        resource.refresh_from_db()
        self.assertEqual(resource.preview_count, 1)
        self.assertEqual(first_claim.status_code, 200)
        self.assertEqual(second_claim.json()["data"], first_claim.json()["data"])
        self.assertEqual(inbox.json()["data"]["count"], 1)
        item = inbox.json()["data"]["items"][0]
        self.assertEqual(item["sender"], "Ana")

        updated = self.client.patch(
            f"/api/v1/shares/inbox/{item['id']}",
            data={"is_read": True, "is_favorite": True},
            content_type="application/json",
        )
        saved = self.client.post(f"/api/v1/shares/inbox/{item['id']}/save")
        dismissed = self.client.patch(
            f"/api/v1/shares/inbox/{item['id']}",
            data={"dismissed": True},
            content_type="application/json",
        )

        self.assertTrue(updated.json()["data"]["is_read"])
        self.assertTrue(updated.json()["data"]["is_favorite"])
        self.assertEqual(saved.json()["data"]["entity"], "dailyPlan")
        self.assertEqual(dismissed.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/shares/inbox").json()["data"]["count"], 0)

    @override_settings(RATE_LIMIT_SHARING_CREATE_USER="1/h")
    def test_share_creation_has_a_json_rate_limit(self):
        cache.clear()
        first_plan = DailyPlan.objects.create(name="Uno", created_by=self.user, is_draft=False)
        second_plan = DailyPlan.objects.create(name="Dos", created_by=self.user, is_draft=False)
        try:
            first = self.client.post(
                f"/api/v1/shares/daily-plans/{first_plan.id}",
                data={},
                content_type="application/json",
            )
            second = self.client.post(
                f"/api/v1/shares/daily-plans/{second_plan.id}",
                data={},
                content_type="application/json",
            )
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 429)
            self.assertEqual(second.json()["error"]["code"], "sharing_create_rate_limited")
        finally:
            cache.clear()

    @override_settings(RATE_LIMIT_SHARING_PREVIEW_IP="1/h")
    def test_public_api_preview_has_an_ip_rate_limit(self):
        cache.clear()
        resource = ShareResource.objects.create(
            sender=self.user,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            snapshot={"subject": {"title": "Limitado"}},
            snapshot_schema_version="sharing.snapshot.v1",
        )
        anonymous = Client(REMOTE_ADDR="203.0.113.20")
        try:
            first = anonymous.get(f"/api/v1/shares/{resource.public_id}")
            second = anonymous.get(f"/api/v1/shares/{resource.public_id}")
            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 429)
            self.assertEqual(second.json()["error"]["code"], "sharing_preview_rate_limited")
        finally:
            cache.clear()
