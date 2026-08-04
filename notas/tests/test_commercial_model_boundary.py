from django.contrib.auth import get_user_model
from django.test import TestCase

from notas.domain.models import NutritionistMemberRelationship, Subscription


class CommercialModelBoundaryTests(TestCase):
    def test_nutrition_relationship_facade_uses_historical_table_without_copying_data(self):
        nutritionist = get_user_model().objects.create_user(username="nutritionist")
        member = get_user_model().objects.create_user(username="member")
        relationship = Subscription.objects.create(nutritionist=nutritionist, member=member)

        facade = NutritionistMemberRelationship.objects.get(pk=relationship.pk)

        self.assertTrue(NutritionistMemberRelationship._meta.proxy)
        self.assertIs(NutritionistMemberRelationship._meta.concrete_model, Subscription)
        self.assertEqual(facade.member, member)
        self.assertEqual(facade.nutritionist, nutritionist)
