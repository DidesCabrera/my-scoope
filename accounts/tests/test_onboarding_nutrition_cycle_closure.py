from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from notas.application.ai_intake.dailyplan_generator import build_dailyplan_target_plan
from notas.application.ai_intake.nutrition_brief import start_or_continue_conversation
from notas.application.dto.nutrition_subject_context_dto import (
    PPK_WEIGHT_SOURCE_EXTERNAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
    SUBJECT_SOURCE_SELF_PROFILE,
)
from notas.application.proposals.subject_context_warnings import (
    proposal_requires_external_subject_ack,
)
from notas.domain.models import NutritionProposal, Profile, WeightLog


User = get_user_model()


class OnboardingNutritionCycleClosureTests(TestCase):
    def _complete_onboarding_through_ui(self, user, *, weight_kg="88.5"):
        self.client.force_login(user)
        response = self.client.post(
            reverse("accounts:nutrition_onboarding"),
            {
                "birth_date": "1988-01-17",
                "sex": Profile.SEX_MALE,
                "height_cm": "188",
                "weight_kg": weight_kg,
            },
        )
        self.assertRedirects(response, reverse("home_view"))

    def test_self_profile_flow_uses_onboarding_body_metrics_for_solver_subject(self):
        user = User.objects.create_user(
            username="onb09_self",
            email="onb09_self@example.com",
            password="12345678",
        )

        self._complete_onboarding_through_ui(user)
        user.refresh_from_db()

        profile = user.profile
        profile.refresh_from_db()
        self.assertEqual(profile.birth_date, date(1988, 1, 17))
        self.assertEqual(profile.sex, Profile.SEX_MALE)
        self.assertEqual(profile.height_cm, 188)
        self.assertEqual(profile.onboarding_version, Profile.ONBOARDING_VERSION_NUTRITION_V1)

        weight_log = user.weight_logs.get()
        self.assertEqual(weight_log.weight_kg, 88.5)
        self.assertEqual(weight_log.source, WeightLog.SOURCE_ONBOARDING)

        state = start_or_continue_conversation(
            user=user,
            message=(
                "usa mi ficha para bajar grasa, 4 comidas, simple, "
                "actividad moderada y entreno 3 dias"
            ),
        )
        brief = state.result.brief

        self.assertTrue(state.is_ready_for_proposal)
        self.assertEqual(brief.subject_source, SUBJECT_SOURCE_SELF_PROFILE)
        self.assertEqual(brief.ppk_weight_source, PPK_WEIGHT_SOURCE_PROFILE)
        self.assertEqual(brief.weight_kg, 88.5)
        self.assertEqual(brief.height_cm, 188)
        self.assertEqual(brief.sex, Profile.SEX_MALE)
        self.assertFalse(brief.requires_library_ppk_warning)

        target_plan = build_dailyplan_target_plan(user=user, brief=brief)
        subject_context = target_plan.as_targets_dict()["subject_context"]

        self.assertEqual(target_plan.weight_kg, 88.5)
        self.assertEqual(subject_context["source"], SUBJECT_SOURCE_SELF_PROFILE)
        self.assertEqual(subject_context["ppk_weight_source"], PPK_WEIGHT_SOURCE_PROFILE)
        self.assertFalse(subject_context["requires_library_ppk_warning"])

    def test_external_subject_flow_keeps_external_weight_and_requires_library_ack(self):
        user = User.objects.create_user(
            username="onb09_external",
            email="onb09_external@example.com",
            password="12345678",
        )
        self._complete_onboarding_through_ui(user, weight_kg="90")

        state = start_or_continue_conversation(
            user=user,
            message=(
                "es para otra persona: bajar grasa, 4 comidas, simple, "
                "peso 70 kg, altura 165 cm, 28 años, mujer, actividad ligera"
            ),
        )
        brief = state.result.brief

        self.assertTrue(state.is_ready_for_proposal)
        self.assertEqual(brief.subject_source, SUBJECT_SOURCE_EXTERNAL_CHAT_DATA)
        self.assertEqual(brief.ppk_weight_source, PPK_WEIGHT_SOURCE_EXTERNAL)
        self.assertEqual(brief.weight_kg, 70)
        self.assertEqual(brief.height_cm, 165)
        self.assertEqual(brief.age_years, 28)
        self.assertEqual(brief.sex, Profile.SEX_FEMALE)
        self.assertTrue(brief.requires_library_ppk_warning)

        target_plan = build_dailyplan_target_plan(user=user, brief=brief)
        subject_context = target_plan.as_targets_dict()["subject_context"]

        self.assertEqual(target_plan.weight_kg, 70)
        self.assertEqual(subject_context["source"], SUBJECT_SOURCE_EXTERNAL_CHAT_DATA)
        self.assertEqual(subject_context["ppk_weight_source"], PPK_WEIGHT_SOURCE_EXTERNAL)
        self.assertEqual(subject_context["calculation_weight_kg"], 70)
        self.assertTrue(subject_context["requires_library_ppk_warning"])

        proposal = NutritionProposal.objects.create(
            created_by=user,
            status=NutritionProposal.STATUS_APPROVED,
            title="External subject proposal",
            targets={"subject_context": subject_context},
        )

        self.assertTrue(proposal_requires_external_subject_ack(proposal))
