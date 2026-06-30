from django.http import Http404
from django.test import TestCase

from notas.domain.models import Food
from notas.presentation.pages.object_lookup import get_page_object_or_404


class PresentationPageObjectLookupTests(TestCase):
    def test_get_page_object_or_404_returns_matching_object(self):
        food = Food.objects.create(
            name="Arroz",
            protein=2,
            carbs=28,
            fat=0.3,
        )

        result = get_page_object_or_404(Food.objects.all(), pk=food.pk)

        self.assertEqual(result, food)

    def test_get_page_object_or_404_raises_http404_when_missing(self):
        with self.assertRaises(Http404):
            get_page_object_or_404(Food.objects.none(), pk=999)
