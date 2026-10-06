from mobile_api.tests.base import AuthenticatedMobileAPITestCase


class MobileLearningAPITests(AuthenticatedMobileAPITestCase):
    def test_learning_catalog_exposes_foundations_and_manuals(self):
        response = self.client.get("/api/v1/learning")

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()["data"]
        self.assertEqual(len(data["nutrition"]), 6)
        self.assertEqual(len(data["manuals"]), 6)
        self.assertEqual(data["nutrition"][0]["slug"], "alimentacion-saludable")
        self.assertEqual(data["manuals"][0]["slug"], "fichas-personales")
