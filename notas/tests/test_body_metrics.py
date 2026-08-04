from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notas.application.services.nutrition.body_metrics import (
    calculate_age_years,
    get_basic_body_profile,
    get_current_weight,
    get_current_weight_log,
    record_weight,
)
from notas.domain.models import Profile, WeightLog

User = get_user_model()


class BodyMetricsServiceTests(TestCase):
    def test_profile_stores_onboarding_body_basics(self):
        user = User.objects.create_user(
            username="onboarding_profile",
            email="onboarding_profile@test.com",
            password="12345678",
        )
        completed_at = timezone.now()

        profile = user.profile
        profile.birth_date = date(1988, 1, 17)
        profile.sex = Profile.SEX_MALE
        profile.height_cm = 188
        profile.onboarding_completed_at = completed_at
        profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.save(update_fields=[
            "birth_date",
            "sex",
            "height_cm",
            "onboarding_completed_at",
            "onboarding_version",
        ])

        self.assertEqual(profile.birth_date, date(1988, 1, 17))
        self.assertEqual(profile.sex, Profile.SEX_MALE)
        self.assertEqual(profile.height_cm, 188)
        self.assertEqual(profile.onboarding_completed_at, completed_at)
        self.assertEqual(profile.onboarding_version, 1)

    def test_calculate_age_years_uses_birth_date_dynamically(self):
        birth_date = date(1988, 1, 17)

        self.assertEqual(calculate_age_years(birth_date, date(2026, 1, 16)), 37)
        self.assertEqual(calculate_age_years(birth_date, date(2026, 1, 17)), 38)
        self.assertIsNone(calculate_age_years(None, date(2026, 1, 17)))

    def test_record_weight_creates_body_metric_with_source(self):
        user = User.objects.create_user(
            username="weight_source",
            email="weight_source@test.com",
            password="12345678",
        )

        log = record_weight(
            user,
            88.5,
            measured_on=date(2026, 7, 3),
            source=WeightLog.SOURCE_ONBOARDING,
        )

        self.assertEqual(log.weight_kg, 88.5)
        self.assertEqual(log.date, date(2026, 7, 3))
        self.assertEqual(log.source, WeightLog.SOURCE_ONBOARDING)
        self.assertEqual(get_current_weight(user), 88.5)
        self.assertEqual(get_current_weight_log(user), log)

    def test_record_weight_updates_metric_for_same_day(self):
        user = User.objects.create_user(
            username="weight_update",
            email="weight_update@test.com",
            password="12345678",
        )

        first = record_weight(user, 90, measured_on=date(2026, 7, 3))
        second = record_weight(user, 89, measured_on=date(2026, 7, 3))

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(WeightLog.objects.count(), 1)
        self.assertEqual(second.weight_kg, 89)

    def test_get_basic_body_profile_combines_profile_and_current_weight(self):
        user = User.objects.create_user(
            username="body_profile",
            email="body_profile@test.com",
            password="12345678",
        )
        profile = user.profile
        profile.birth_date = date(1988, 1, 17)
        profile.sex = Profile.SEX_MALE
        profile.height_cm = 188
        profile.onboarding_completed_at = timezone.now()
        profile.onboarding_version = Profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.save(update_fields=[
            "birth_date",
            "sex",
            "height_cm",
            "onboarding_completed_at",
            "onboarding_version",
        ])
        record_weight(
            user,
            88,
            measured_on=date(2026, 7, 3),
            source=WeightLog.SOURCE_ONBOARDING,
        )

        body_profile = get_basic_body_profile(user)

        self.assertEqual(body_profile.birth_date, date(1988, 1, 17))
        self.assertEqual(body_profile.sex, Profile.SEX_MALE)
        self.assertEqual(body_profile.height_cm, 188)
        self.assertEqual(body_profile.current_weight_kg, 88)
        self.assertEqual(body_profile.onboarding_version, 1)
        self.assertTrue(body_profile.is_complete_for_onboarding_basics)

    def test_get_basic_body_profile_is_safe_without_profile(self):
        user = User.objects.create_user(
            username="without_profile",
            email="without_profile@test.com",
            password="12345678",
        )

        user.profile.delete()

        body_profile = get_basic_body_profile(user)

        self.assertIsNone(body_profile.birth_date)
        self.assertEqual(body_profile.sex, "")
        self.assertIsNone(body_profile.current_weight_kg)
        self.assertFalse(body_profile.is_complete_for_onboarding_basics)
