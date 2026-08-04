from django.test import TestCase
from django.urls import reverse

from notas.presentation.config.viewmodel_config import (
    FOOD_VIEWMODE_PERSONAL_DETAIL,
    FOOD_VIEWMODE_PERSONAL_LIST,
    PROFILE_VIEWMODE,
)
from notas.presentation.navigation.nav_builders import build_back_url


class DummyParentWithAbsoluteUrl:
    def get_absolute_url(self):
        return "/dummy-parent/"


class NavigationBackUrlTests(TestCase):

    def test_build_back_url_returns_none_for_list_mode(self):
        back_url = build_back_url(FOOD_VIEWMODE_PERSONAL_LIST)

        self.assertIsNone(back_url)

    def test_build_back_url_returns_parent_url_when_parent_exists(self):
        back_url = build_back_url(
            FOOD_VIEWMODE_PERSONAL_DETAIL,
            parents=[DummyParentWithAbsoluteUrl()],
        )

        self.assertEqual(back_url, "/dummy-parent/")

    def test_build_back_url_returns_active_item_url_when_no_parent_exists(self):
        back_url = build_back_url(FOOD_VIEWMODE_PERSONAL_DETAIL)

        self.assertEqual(back_url, reverse("food_list"))

    def test_build_back_url_returns_none_for_profile_list(self):
        back_url = build_back_url(PROFILE_VIEWMODE)

        self.assertIsNone(back_url)







