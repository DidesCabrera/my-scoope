from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase

from mobile_api.architecture import route_domain

ROOT = Path(__file__).resolve().parents[2]


class MobileAPIArchitectureTests(SimpleTestCase):
    def test_every_v1_route_has_an_explicit_domain_owner(self):
        routes = []
        route_files = [ROOT / "mobile_api/api.py", *(ROOT / "mobile_api/routes").glob("*.py")]
        for route_file in route_files:
            tree = ast.parse(route_file.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call) or not decorator.args:
                        continue
                    function = decorator.func
                    if not (
                        isinstance(function, ast.Attribute)
                        and isinstance(function.value, ast.Name)
                        and function.value.id in {"api", "router"}
                        and function.attr in {"delete", "get", "patch", "post", "put"}
                    ):
                        continue
                    if isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                        routes.append((node.name, decorator.args[0].value))

        self.assertGreaterEqual(len(routes), 79)
        unowned = [f"{name}: {path}" for name, path in routes if route_domain(path) is None]
        self.assertEqual(unowned, [])

    def test_support_helpers_are_outside_the_route_registry_facade(self):
        source = (ROOT / "mobile_api/api.py").read_text()

        self.assertIn("from mobile_api.api_support import", source)
        self.assertNotIn("def _calendarization_error", source)
        self.assertNotIn("def _proposal_error", source)

    def test_extracted_domains_are_owned_outside_the_route_and_schema_facades(self):
        api_source = (ROOT / "mobile_api/api.py").read_text()
        schema_source = (ROOT / "mobile_api/schemas.py").read_text()

        self.assertIn('api.add_router("", billing_router)', api_source)
        self.assertIn('api.add_router("", calendarization_router)', api_source)
        self.assertIn('api.add_router("", comparisons_router)', api_source)
        self.assertIn('api.add_router("", composition_router)', api_source)
        self.assertIn('api.add_router("", identity_router)', api_source)
        self.assertIn('api.add_router("", libraries_router)', api_source)
        self.assertIn('api.add_router("", proposals_router)', api_source)
        self.assertNotIn("def active_program", api_source)
        self.assertNotIn("def apple_transaction", api_source)
        self.assertNotIn("def comparison_metadata", api_source)
        self.assertNotIn("def library_item_detail", api_source)
        self.assertNotIn("def meal_food_picker_commit", api_source)
        self.assertNotIn("def onboarding", api_source)
        self.assertNotIn("def proposal_detail", api_source)
        self.assertIn("from mobile_api.schema_domains.billing import", schema_source)
        self.assertIn("from mobile_api.schema_domains.calendarization import", schema_source)
        self.assertIn("from mobile_api.schema_domains.comparisons import", schema_source)
        self.assertIn("from mobile_api.schema_domains.composition import", schema_source)
        self.assertIn("from mobile_api.schema_domains.identity import", schema_source)
        self.assertIn("from mobile_api.schema_domains.libraries import", schema_source)
        self.assertIn("from mobile_api.schema_domains.proposals import", schema_source)
        self.assertNotIn("class TodayData", schema_source)
        self.assertNotIn("class SubscriptionData", schema_source)
        self.assertNotIn("class ComparisonResultData", schema_source)
        self.assertNotIn("class LibraryItemData", schema_source)
        self.assertNotIn("class PickerPreviewData", schema_source)
        self.assertNotIn("class ProfileData", schema_source)
        self.assertNotIn("class ProposalDetailData", schema_source)

    def test_extracted_routes_pin_their_public_operation_ids(self):
        for route_file in (ROOT / "mobile_api/routes").glob("*.py"):
            tree = ast.parse(route_file.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call):
                        continue
                    function = decorator.func
                    if not (
                        isinstance(function, ast.Attribute)
                        and isinstance(function.value, ast.Name)
                        and function.value.id == "router"
                        and function.attr in {"delete", "get", "patch", "post", "put"}
                    ):
                        continue
                    keyword_names = {keyword.arg for keyword in decorator.keywords}
                    self.assertIn("operation_id", keyword_names, f"{route_file.name}:{node.name}")
