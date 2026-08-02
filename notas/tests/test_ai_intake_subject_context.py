from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from notas.application.ai_intake.nutrition_brief import (
    build_intake_result,
    start_or_continue_conversation,
)
from notas.application.dto.nutrition_subject_context_dto import (
    PPK_WEIGHT_SOURCE_EXTERNAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
    SUBJECT_SOURCE_MANUAL_CHAT_DATA,
    SUBJECT_SOURCE_SELF_PROFILE,
)
from notas.application.services.nutrition.body_metrics import record_weight
from notas.domain.models import Profile, WeightLog


class AiIntakeSubjectContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="subject-user",
            email="subject@example.com",
            password="pass123",
        )
        profile = self.user.profile
        profile.birth_date = date(1990, 1, 15)
        profile.sex = Profile.SEX_MALE
        profile.height_cm = 180
        profile.onboarding_completed_at = timezone.now()
        profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.save()
        record_weight(self.user, weight_kg=88, source=WeightLog.SOURCE_ONBOARDING)

    def test_initial_request_does_not_block_on_subject_source(self):
        result = build_intake_result("quiero bajar grasa")

        self.assertIsNone(result.brief.subject_source)
        self.assertNotIn("ficha personal", " ".join(result.required_follow_up_questions).lower())
        self.assertIn(
            "peso actual",
            " ".join(result.required_follow_up_questions).lower(),
        )

    def test_self_profile_choice_prefills_body_basics_and_only_needs_chat_activity(self):
        state = start_or_continue_conversation(
            user=self.user,
            message="usa mi ficha para bajar grasa, 4 comidas, simple, actividad moderada y entreno 3 dias",
        )
        brief = state.result.brief

        self.assertEqual(brief.subject_source, SUBJECT_SOURCE_SELF_PROFILE)
        self.assertEqual(brief.ppk_weight_source, PPK_WEIGHT_SOURCE_PROFILE)
        self.assertEqual(brief.weight_kg, 88)
        self.assertEqual(brief.height_cm, 180)
        self.assertEqual(brief.sex, Profile.SEX_MALE)
        self.assertEqual(brief.activity_level, "moderate")
        self.assertEqual(brief.training_frequency, 3)
        self.assertTrue(state.is_ready_for_proposal)
        self.assertFalse(brief.requires_library_ppk_warning)

    def test_external_subject_uses_chat_weight_for_calculation_and_ppk_warning(self):
        state = start_or_continue_conversation(
            user=self.user,
            message=(
                "es para otra persona: bajar grasa, 4 comidas, simple, peso 70 kg, "
                "altura 165 cm, 28 años, mujer, actividad ligera"
            ),
        )
        brief = state.result.brief

        self.assertEqual(brief.subject_source, SUBJECT_SOURCE_EXTERNAL_CHAT_DATA)
        self.assertEqual(brief.ppk_weight_source, PPK_WEIGHT_SOURCE_EXTERNAL)
        self.assertEqual(brief.weight_kg, 70)
        self.assertEqual(brief.height_cm, 165)
        self.assertEqual(brief.age_years, 28)
        self.assertEqual(brief.sex, Profile.SEX_FEMALE)
        self.assertTrue(brief.requires_library_ppk_warning)
        self.assertTrue(state.is_ready_for_proposal)

    def test_manual_body_data_is_treated_as_temporary_subject_without_profile_fallback(self):
        result = build_intake_result(
            "bajar grasa 4 comidas simple peso 70 kg altura 165 cm 28 años mujer actividad ligera"
        )

        self.assertEqual(result.brief.subject_source, SUBJECT_SOURCE_MANUAL_CHAT_DATA)
        self.assertEqual(result.brief.weight_kg, 70)
        self.assertTrue(result.is_ready_for_proposal)
