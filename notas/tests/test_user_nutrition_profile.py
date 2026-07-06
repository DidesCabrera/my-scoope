from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone

from notas.application.dto.nutrition_subject_context_dto import (
    PPK_WEIGHT_SOURCE_EXTERNAL,
    PPK_WEIGHT_SOURCE_PROFILE,
    SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
    SUBJECT_SOURCE_SELF_PROFILE,
)
from notas.application.queries.user_nutrition_profile import (
    NutritionSubjectContextError,
    build_nutrition_subject_context,
    get_user_nutrition_profile,
)
from notas.application.services.nutrition.body_metrics import (
    calculate_age_years,
    record_weight,
)
from notas.domain.models import Profile, WeightLog


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class UserNutritionProfileQueryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="pass123")
        self.profile = self.user.profile
        self.profile.birth_date = date(1988, 1, 17)
        self.profile.sex = Profile.SEX_MALE
        self.profile.height_cm = 188
        self.profile.onboarding_completed_at = timezone.now()
        self.profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        self.profile.save()

    def test_get_user_nutrition_profile_combines_profile_and_current_weight(self):
        record_weight(
            self.user,
            88,
            measured_on=date(2026, 7, 1),
            source=WeightLog.SOURCE_ONBOARDING,
        )

        dto = get_user_nutrition_profile(self.user)
        data = dto.as_dict()

        self.assertEqual(data["user_id"], self.user.id)
        self.assertEqual(data["username"], "felipe")
        self.assertEqual(data["birth_date"], "1988-01-17")
        self.assertEqual(data["age_years"], calculate_age_years(date(1988, 1, 17)))
        self.assertEqual(data["sex"], Profile.SEX_MALE)
        self.assertEqual(data["height_cm"], 188)
        self.assertEqual(data["current_weight_kg"], 88.0)
        self.assertEqual(data["current_weight_date"], "2026-07-01")
        self.assertEqual(data["current_weight_source"], WeightLog.SOURCE_ONBOARDING)
        self.assertTrue(data["is_complete_for_body_basics"])
        self.assertFalse(data["is_complete_for_energy_estimation"])

    def test_self_profile_subject_uses_profile_body_data_and_chat_activity(self):
        record_weight(self.user, 88, measured_on=date(2026, 7, 1))

        subject = build_nutrition_subject_context(
            user=self.user,
            source=SUBJECT_SOURCE_SELF_PROFILE,
            chat_context={
                "activity_level": "moderate",
                "training_frequency": 3,
            },
        )
        data = subject.as_dict()

        self.assertTrue(data["is_self_profile"])
        self.assertFalse(data["is_external"])
        self.assertEqual(data["weight_kg"], 88.0)
        self.assertEqual(data["height_cm"], 188)
        self.assertEqual(data["age_years"], calculate_age_years(date(1988, 1, 17)))
        self.assertEqual(data["sex"], Profile.SEX_MALE)
        self.assertEqual(data["activity_level"], "moderate")
        self.assertEqual(data["training_frequency"], 3)
        self.assertEqual(data["ppk_weight_source"], PPK_WEIGHT_SOURCE_PROFILE)
        self.assertTrue(data["is_complete_for_energy_estimation"])
        self.assertFalse(data["requires_library_ppk_warning"])

    def test_external_subject_uses_external_chat_data_for_ppk_and_calculation(self):
        record_weight(self.user, 88, measured_on=date(2026, 7, 1))

        subject = build_nutrition_subject_context(
            user=self.user,
            source=SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
            chat_context={
                "weight_kg": 70,
                "height_cm": 174,
                "age_years": 30,
                "sex": "female",
                "activity_level": "light",
                "training_frequency": 2,
            },
        )
        data = subject.as_dict()

        self.assertFalse(data["is_self_profile"])
        self.assertTrue(data["is_external"])
        self.assertEqual(data["weight_kg"], 70.0)
        self.assertEqual(data["height_cm"], 174)
        self.assertEqual(data["age_years"], 30)
        self.assertEqual(data["sex"], "female")
        self.assertEqual(data["activity_level"], "light")
        self.assertEqual(data["training_frequency"], 2)
        self.assertEqual(data["ppk_weight_source"], PPK_WEIGHT_SOURCE_EXTERNAL)
        self.assertEqual(data["calculation_weight_kg"], 70.0)
        self.assertTrue(data["is_complete_for_energy_estimation"])
        self.assertTrue(data["requires_library_ppk_warning"])

    def test_external_subject_can_calculate_age_from_birth_date(self):
        subject = build_nutrition_subject_context(
            user=self.user,
            source=SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
            chat_context={
                "weight_kg": "70",
                "height_cm": "174",
                "birth_date": "1996-07-03",
                "sex": "female",
                "activity_level": "light",
            },
        )

        self.assertEqual(subject.age_years, calculate_age_years(date(1996, 7, 3)))
        self.assertTrue(subject.is_complete_for_energy_estimation)

    def test_external_subject_does_not_fallback_to_owner_body_data(self):
        record_weight(self.user, 88, measured_on=date(2026, 7, 1))

        subject = build_nutrition_subject_context(
            user=self.user,
            source=SUBJECT_SOURCE_EXTERNAL_CHAT_DATA,
            chat_context={"activity_level": "moderate"},
        )

        self.assertIsNone(subject.weight_kg)
        self.assertIsNone(subject.height_cm)
        self.assertIsNone(subject.age_years)
        self.assertIsNone(subject.sex)
        self.assertFalse(subject.is_complete_for_energy_estimation)
        self.assertTrue(subject.requires_library_ppk_warning)

    def test_unknown_subject_source_fails_explicitly(self):
        with self.assertRaises(NutritionSubjectContextError):
            build_nutrition_subject_context(
                user=self.user,
                source="unsupported",
                chat_context={},
            )
