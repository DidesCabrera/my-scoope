import json
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from notas.domain.models import (
    DailyPlan,
    NutritionProposal,
    WeightLog,
)


def json_post(
    client,
    url_name: str,
    payload: dict | None = None,
    token: str | None = None,
):
    from django.urls import reverse

    headers = {}

    if token is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    return client.post(
        reverse(url_name),
        data=json.dumps(payload or {}),
        content_type="application/json",
        **headers,
    )


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AIToolsAPIInternalAuthIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )

        WeightLog.objects.create(
            user=self.user,
            date=date.today(),
            weight_kg=100,
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )

        self.other_dailyplan = DailyPlan.objects.create(
            name="Other Private Plan",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
        )

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Existing proposal",
            targets={
                "protein": 190,
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

    def assert_success_response(self, response):
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertEqual(
            set(data.keys()),
            {
                "ok",
                "data",
                "error",
            },
        )
        self.assertTrue(data["ok"])
        self.assertIsInstance(data["data"], dict)
        self.assertIsNone(data["error"])

        return data

    def assert_error_response(self, response, code: str, status_code: int = 401):
        self.assertEqual(response.status_code, status_code)

        data = response.json()

        self.assertEqual(
            set(data.keys()),
            {
                "ok",
                "data",
                "error",
            },
        )
        self.assertFalse(data["ok"])
        self.assertEqual(data["data"], {})
        self.assertIsInstance(data["error"], dict)
        self.assertEqual(data["error"]["code"], code)

        return data

    def test_session_auth_still_works(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_list_user_proposals",
            {},
        )

        data = self.assert_success_response(response)

        proposal_ids = [
            proposal["id"]
            for proposal in data["data"]["proposals"]
        ]

        self.assertIn(
            self.proposal.id,
            proposal_ids,
        )

    def test_internal_auth_allows_list_user_proposals(self):
        with self._env(
            token="dev-token",
            username="felipe",
        ):
            response = json_post(
                self.client,
                "ai_tools_list_user_proposals",
                {},
                token="dev-token",
            )

        data = self.assert_success_response(response)

        proposal_ids = [
            proposal["id"]
            for proposal in data["data"]["proposals"]
        ]

        self.assertIn(
            self.proposal.id,
            proposal_ids,
        )

    def test_internal_auth_allows_read_dailyplan(self):
        with self._env(
            token="dev-token",
            username="felipe",
        ):
            response = json_post(
                self.client,
                "ai_tools_read_dailyplan",
                {
                    "dailyplan_id": self.dailyplan.id,
                },
                token="dev-token",
            )

        data = self.assert_success_response(response)

        self.assertEqual(
            data["data"]["dailyplan"]["id"],
            self.dailyplan.id,
        )

    def test_internal_auth_blocks_invalid_token(self):
        with self._env(
            token="dev-token",
            username="felipe",
        ):
            response = json_post(
                self.client,
                "ai_tools_list_user_proposals",
                {},
                token="wrong-token",
            )

        self.assert_error_response(
            response,
            "internal_api_auth_invalid",
        )

    def test_internal_auth_blocks_missing_configured_token(self):
        with self._env(
            token=None,
            username="felipe",
        ):
            response = json_post(
                self.client,
                "ai_tools_list_user_proposals",
                {},
                token="dev-token",
            )

        self.assert_error_response(
            response,
            "internal_api_auth_not_configured",
        )

    def test_internal_auth_blocks_missing_configured_username(self):
        with self._env(
            token="dev-token",
            username=None,
        ):
            response = json_post(
                self.client,
                "ai_tools_list_user_proposals",
                {},
                token="dev-token",
            )

        self.assert_error_response(
            response,
            "internal_api_auth_user_not_configured",
        )

    def test_internal_auth_blocks_unknown_user(self):
        with self._env(
            token="dev-token",
            username="unknown",
        ):
            response = json_post(
                self.client,
                "ai_tools_list_user_proposals",
                {},
                token="dev-token",
            )

        data = self.assert_error_response(
            response,
            "internal_api_auth_user_not_found",
        )

        self.assertEqual(
            data["error"]["details"],
            {
                "username": "unknown",
            },
        )

    def test_internal_auth_blocks_inactive_user(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self._env(
            token="dev-token",
            username="felipe",
        ):
            response = json_post(
                self.client,
                "ai_tools_list_user_proposals",
                {},
                token="dev-token",
            )

        self.assert_error_response(
            response,
            "internal_api_auth_user_inactive",
        )

    def test_internal_auth_does_not_allow_payload_user_id_impersonation(self):
        with self._env(
            token="dev-token",
            username="felipe",
        ):
            response = json_post(
                self.client,
                "ai_tools_read_dailyplan",
                {
                    "user_id": self.other_user.id,
                    "dailyplan_id": self.other_dailyplan.id,
                },
                token="dev-token",
            )

        data = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "not_found",
        )

    def _env(self, token: str | None, username: str | None):
        return TemporaryEnv(
            {
                "MYSCOOPE_INTERNAL_API_TOKEN": token,
                "MYSCOOPE_INTERNAL_API_USERNAME": username,
            }
        )


class TemporaryEnv:
    def __init__(self, values):
        self.values = values
        self.previous = {}

    def __enter__(self):
        import os

        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)

            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

        return self

    def __exit__(self, exc_type, exc, traceback):
        import os

        for key, previous_value in self.previous.items():
            if previous_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous_value

        return False