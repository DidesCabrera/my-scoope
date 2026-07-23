import ast
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_knowledge.policy import (
    HUMAN_REFERENCE_MARKERS,
    KNOWLEDGE_DOCUMENT_PATHS,
    POLICY,
)
from admin_knowledge.services import discover_documents, load_document


ROOT = Path(__file__).resolve().parents[2]


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AdminKnowledgeAccessTests(TestCase):
    def _staff_user(self, suffix="staff"):
        User = get_user_model()
        user = User.objects.create_user(
            username=f"{suffix}@example.com",
            email=f"{suffix}@example.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_login(user)
        return user

    def test_overview_requires_login(self):
        response = self.client.get(reverse("admin_knowledge_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_overview_rejects_non_staff_user(self):
        User = get_user_model()
        user = User.objects.create_user(
            username="member-knowledge@example.com",
            email="member-knowledge@example.com",
            password="password123",
            is_staff=False,
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin_knowledge_overview"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_overview_is_an_independent_app_connected_to_admin_hub(self):
        self._staff_user("knowledge-shell")

        response = self.client.get(reverse("admin_knowledge_overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Knowledge Center")
        self.assertContains(response, "Human Reference")
        self.assertContains(response, "Admin Hub")
        self.assertContains(response, "Analytics")
        self.assertContains(response, "Operations")
        self.assertContains(response, "Guías para personas")
        self.assertContains(response, "Orientación para personas, no fuente de verdad")
        self.assertContains(response, "Solo se actualiza cuando Felipe lo solicita explícitamente")
        html = response.content.decode("utf-8")
        self.assertIn('class="admin-analytics-shell admin-knowledge-shell"', html)
        self.assertNotIn('class="app-body"', html)

    def test_ai_assistant_document_renders_latest_capability_parity(self):
        self._staff_user("knowledge-ai")
        response = self.client.get(
            reverse(
                "admin_knowledge_document",
                kwargs={
                    "document_path": (
                        "00_current/features/admin_knowledge/ai_assistant.md"
                    )
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Assistant: paridad, seguridad y operación")
        self.assertContains(response, "aumenta este plan en 200 calorías")
        self.assertContains(response, "snapshots independientes")
        self.assertContains(response, "AIPreparedAction")
        self.assertContains(
            response,
            "/staff/knowledge/documents/00_current/features/admin_knowledge/README.md",
        )

    def test_search_uses_only_explicit_human_catalog(self):
        self._staff_user("knowledge-search")

        response = self.client.get(
            reverse("admin_knowledge_overview"),
            {"q": "snapshots independientes"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "coincidencias para")
        self.assertContains(response, "AI Assistant: paridad, seguridad y operación")
        self.assertNotContains(response, "AI Assistant System Capability Parity Cycle")

    def test_unknown_or_non_markdown_document_returns_404(self):
        self._staff_user("knowledge-missing")

        response = self.client.get(
            reverse(
                "admin_knowledge_document",
                kwargs={"document_path": "00_current/missing.md"},
            )
        )
        non_markdown = self.client.get(
            reverse(
                "admin_knowledge_document",
                kwargs={"document_path": "00_current/PROJECT_STATE.py"},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(non_markdown.status_code, 404)


class AdminKnowledgeServiceTests(TestCase):
    def test_policy_makes_human_non_authoritative_boundary_executable(self):
        self.assertEqual(POLICY.audience, "human_staff")
        self.assertFalse(POLICY.authoritative)
        self.assertFalse(POLICY.codex_context_source)
        self.assertFalse(POLICY.automatic_discovery)
        self.assertFalse(POLICY.automatic_cycle_updates)
        self.assertTrue(POLICY.requires_explicit_owner_request)
        self.assertFalse(POLICY.product_dependencies_allowed)

    def test_discovery_is_limited_to_explicit_human_manifest(self):
        documents = discover_documents()

        self.assertEqual(
            tuple(item.relative_path for item in documents),
            KNOWLEDGE_DOCUMENT_PATHS,
        )
        self.assertTrue(all(item.collection_key == "human_guides" for item in documents))

    def test_every_human_guide_declares_non_authoritative_update_policy(self):
        for relative_path in KNOWLEDGE_DOCUMENT_PATHS:
            source = (ROOT / "docs" / relative_path).read_text(encoding="utf-8")
            with self.subTest(relative_path=relative_path):
                for marker in HUMAN_REFERENCE_MARKERS:
                    self.assertIn(marker, source)

    def test_document_loader_blocks_traversal_and_non_markdown_sources(self):
        for unsafe_path in (
            "../requirements.md",
            "00_current/../../requirements.md",
            "/00_current/README.md",
            "00_current/README.txt",
        ):
            with self.subTest(unsafe_path=unsafe_path):
                with self.assertRaises(FileNotFoundError):
                    load_document(unsafe_path)

    def test_non_manifest_markdown_is_not_available_through_the_app(self):
        with self.assertRaises(FileNotFoundError):
            load_document("10_active_cycles/ai_assistant_system_capability_parity_cycle.md")

    def test_product_packages_do_not_depend_on_admin_knowledge(self):
        product_packages = (
            "accounts",
            "ai_assistant",
            "billing",
            "core",
            "food_catalog",
            "nutrition_solver",
            "notas",
        )
        violations = []
        for package in product_packages:
            for path in (ROOT / package).rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        modules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        modules = [node.module or ""]
                    else:
                        continue
                    if any(module == "admin_knowledge" or module.startswith("admin_knowledge.") for module in modules):
                        violations.append(str(path.relative_to(ROOT)))
        self.assertEqual(violations, [])

    def test_root_agent_instructions_exclude_human_center_from_feature_work(self):
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("not a source of truth", instructions)
        self.assertIn("Do not use their wording to infer how the code works", instructions)
        self.assertIn("only when Felipe explicitly requests", instructions)
        self.assertIn("Product code must not import `admin_knowledge`", instructions)
