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
            "MKT",
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
        self.assertContains(response, "Q3-2026")
        self.assertContains(response, "Q4-2026")
        self.assertContains(response, "Roadmap de empresa")
        self.assertContains(response, "Lanzamiento público de My Scoope")
        self.assertContains(response, "Entrar")
        self.assertContains(response, "Alternativas con las que competimos")
        html = response.content.decode("utf-8")
        self.assertLess(html.index(">CEO Dashboard</button>"), html.index(">Manifiesto</button>"))
        manifesto_start = html.index('id="panel-manifesto"')
        document_header = html.index('class="document-header"')
        self.assertGreater(document_header, manifesto_start)

    def test_msos_route_only_allows_get(self):
        self._login(is_staff=True)
        response = self.client.post(reverse("msos"))
        self.assertEqual(response.status_code, 405)

    def test_msos_task_opens_as_full_detail_page_and_returns_to_dashboard(self):
        self._login(is_staff=True)

        response = self.client.get(reverse("msos_detail", args=("task", "launch-readiness")))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/msos_detail.html")
        self.assertContains(response, "Frentes de readiness")
        self.assertContains(response, "Onboarding y activación")
        self.assertContains(response, "Programas semanales y dashboards")
        self.assertContains(response, "Atención al cliente")
        self.assertContains(response, "Planes comerciales y costos")
        self.assertContains(response, '<span class="outline-number">1.</span> Pregunta central', html=True)
        self.assertContains(response, '<span class="outline-number">2.</span> Frentes de readiness', html=True)
        self.assertContains(response, '<span class="outline-number">2.8</span> Planes comerciales y costos', html=True)
        self.assertNotContains(response, '<span class="outline-number"></span>', html=True)
        self.assertNotContains(response, "Ver apuntes")
        self.assertNotContains(response, "Entrar")
        self.assertContains(response, 'href="/msos/front/food-catalog-solver/"')
        self.assertContains(response, 'href="/msos/#ceo-dashboard"')

    def test_msos_front_has_its_own_page_and_returns_to_readiness(self):
        self._login(is_staff=True)

        response = self.client.get(reverse("msos_detail", args=("front", "food-catalog-solver")))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Separar evidencia externa de definición interna")
        self.assertContains(response, "Los nutrientes por 100 g")
        self.assertContains(response, "Automatización asistida")
        self.assertContains(response, "los ambiguos deben ingresar a revisión")
        self.assertContains(response, "Preguntas abiertas")
        self.assertContains(response, 'href="/msos/task/launch-readiness/"')

    def test_msos_project_opens_as_full_detail_page(self):
        self._login(is_staff=True)

        response = self.client.get(reverse("msos_detail", args=("project", "launch26")))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Objetivos")
        self.assertContains(response, "Hitos")
        self.assertContains(response, '<span class="outline-number">1.</span> Objetivos', html=True)
        self.assertContains(response, 'href="/msos/#strategy"')

    def test_msos_departments_are_cards_with_individual_pages(self):
        self._login(is_staff=True)

        overview = self.client.get(reverse("msos"))
        detail = self.client.get(reverse("msos_detail", args=("department", "product")))

        self.assertContains(overview, 'class="department-card"', count=7)
        self.assertContains(overview, 'href="/msos/department/product/"')
        self.assertContains(overview, 'class="department"', count=7)
        self.assertContains(overview, "Detalle por departamento")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Producto")
        self.assertContains(detail, "Mandato del área")
        self.assertContains(detail, "Decisiones pendientes")
        self.assertContains(detail, "Riesgos visibles")
        self.assertContains(detail, "Próxima acción")
        self.assertContains(detail, 'href="/msos/#departments"')

    def test_msos_detail_rejects_unknown_content(self):
        self._login(is_staff=True)
        response = self.client.get(reverse("msos_detail", args=("task", "unknown")))
        self.assertEqual(response.status_code, 404)


class MsosDataTests(SimpleTestCase):
    def test_versioned_source_has_expected_shape(self):
        data = load_msos_data()

        self.assertEqual(data["meta"]["code"], "MSOS00")
        self.assertEqual(len(data["tabs"]), 8)
        self.assertEqual(len(data["departments"]["items"]), 7)
        self.assertEqual(data["departments"]["items"][0]["id"], "product")
        self.assertEqual(len(data["decision_log"]["items"]), 4)
        self.assertEqual(len(data["cycles"]["items"]), 10)
        self.assertEqual(data["tabs"][0]["id"], "ceo-dashboard")
        self.assertEqual(data["tabs"][-1]["id"], "manifesto")
        self.assertEqual([quarter["code"] for quarter in data["strategy"]["quarters"]], ["Q3-2026", "Q4-2026"])
        self.assertEqual(len(data["strategy"]["roadmap"]["projects"]), 4)
        self.assertEqual(data["strategy"]["roadmap"]["projects"][0]["code"], "LAUNCH26")
        self.assertEqual(len(data["mkt"]["target_segments"]), 4)
        self.assertEqual(len(data["ceo_dashboard"]["task_board"]["groups"]), 4)
        self.assertEqual(data["ceo_dashboard"]["task_board"]["groups"][0]["items"][0]["id"], "launch-readiness")
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
