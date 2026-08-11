import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.msos import MSOS_DATA_RELATIVE_PATH, load_msos_data

ROOT = Path(__file__).resolve().parents[2]


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MsosViewTests(TestCase):
    def _login(self, *, is_staff):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"msos-{is_staff}@example.com",
            email=f"msos-{is_staff}@example.com",
            password="password123",
            is_staff=is_staff,
        )
        self.client.force_login(user)

    def test_msos_requires_staff_access(self):
        anonymous = self.client.get(reverse("msos"))
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/admin/login/", anonymous["Location"])

        self._login(is_staff=False)
        member = self.client.get(reverse("msos"))
        self.assertEqual(member.status_code, 302)
        self.assertIn("/admin/login/", member["Location"])

    def test_msos_renders_all_versioned_sections(self):
        self._login(is_staff=True)

        response = self.client.get(reverse("msos"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/msos.html")
        for label in (
            "Manifiesto",
            "Identidad",
            "Estrategia",
            "Departamentos",
            "CEO Dashboard",
            "Decision Log",
            "Ciclos MSOS",
        ):
            self.assertContains(response, label)
        self.assertContains(response, "PLANIFICA → EJECUTA → APRENDE")
        self.assertContains(response, "MSOS09")
        self.assertContains(response, "Solo lectura")
        self.assertContains(response, ">My Scoope Operating System</a>")
        self.assertContains(response, "Pendientes por prioridad")
        self.assertContains(response, "Consolidar el criterio de readiness para lanzamiento")
        html = response.content.decode("utf-8")
        self.assertLess(html.index(">CEO Dashboard</button>"), html.index(">Manifiesto</button>"))
        manifesto_start = html.index('id="panel-manifesto"')
        document_header = html.index('class="document-header"')
        self.assertGreater(document_header, manifesto_start)

    def test_msos_route_only_allows_get(self):
        self._login(is_staff=True)
        response = self.client.post(reverse("msos"))
        self.assertEqual(response.status_code, 405)


class MsosDataTests(SimpleTestCase):
    def test_versioned_source_has_expected_shape(self):
        data = load_msos_data()

        self.assertEqual(data["meta"]["code"], "MSOS00")
        self.assertEqual(len(data["tabs"]), 7)
        self.assertEqual(len(data["departments"]["items"]), 7)
        self.assertEqual(len(data["decision_log"]["items"]), 4)
        self.assertEqual(len(data["cycles"]["items"]), 10)
        self.assertEqual(data["tabs"][0]["id"], "ceo-dashboard")
        self.assertEqual(data["tabs"][-1]["id"], "manifesto")
        self.assertEqual(len(data["ceo_dashboard"]["task_board"]["groups"]), 4)
        self.assertTrue((ROOT / MSOS_DATA_RELATIVE_PATH).is_file())

    def test_loader_rejects_invalid_json(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            path = root / MSOS_DATA_RELATIVE_PATH
            path.parent.mkdir(parents=True)
            path.write_text("not-json", encoding="utf-8")

            with override_settings(BASE_DIR=root):
                with self.assertRaises(ImproperlyConfigured):
                    load_msos_data()

    def test_source_is_valid_json_object(self):
        data = json.loads((ROOT / MSOS_DATA_RELATIVE_PATH).read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
