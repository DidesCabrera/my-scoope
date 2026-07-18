import ast
from pathlib import Path
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NOTAS_ROOT = PROJECT_ROOT / "notas"
DOMAIN_ROOT = NOTAS_ROOT / "domain"
APPLICATION_ROOT = NOTAS_ROOT / "application"
PRESENTATION_ROOT = NOTAS_ROOT / "presentation"
INTERFACE_ROOT = NOTAS_ROOT / "interface"
ROOT_URLCONF = NOTAS_ROOT / "urls.py"
FEATURE_URLS_ROOT = INTERFACE_ROOT / "urls"
MCP_PACKAGE_ROOT = PROJECT_ROOT / "mcp_server" / "myscoope_mcp"
FOOD_CATALOG_ROOT = PROJECT_ROOT / "food_catalog"
SETTINGS_BASE = PROJECT_ROOT / "miapp" / "settings" / "base.py"

APPLICATION_DJANGO_HTTP_IMPORT_ALLOWLIST = {
    "notas/application/ai_tools/errors.py imports django.http",
    "notas/application/queries/proposal_queries.py imports django.shortcuts",
    "notas/application/queries/proposal_queries.py imports django.urls",
    "notas/application/queries/proposal_simulation_queries.py imports django.shortcuts",
    "notas/application/queries/read_boundaries.py imports django.shortcuts",
    "notas/application/services/notifications/share_emails.py imports django.urls",
}

PRESENTATION_DJANGO_HTTP_IMPORT_ALLOWLIST = {
    "notas/presentation/pages/object_lookup.py imports django.shortcuts",
}

APPLICATION_FOOD_CATALOG_IMPORT_ALLOWLIST = {
    "notas/application/dto/imported_food_dto.py imports food_catalog.application.imports.contracts",
    "notas/application/services/commands/food_catalog_backfill.py imports food_catalog.models",
    "notas/application/services/commands/food_catalog_backfill.py imports food_catalog.infrastructure.imports.governance",
    "notas/application/services/food_catalog_snapshots.py imports food_catalog.application.contracts",
    "notas/application/services/food_catalog_snapshots.py imports food_catalog.application.solver_readiness",
    "notas/application/services/food_catalog_snapshots.py imports food_catalog.models",
    "notas/application/services/food_imports/normalization.py imports food_catalog.application.imports.normalization",
    "notas/application/services/food_imports/quality.py imports food_catalog.application.imports.quality",
    "notas/application/services/food_imports/usda/foundation_foods_reader.py imports food_catalog.application.imports.usda.foundation_foods_reader",
    "notas/application/services/food_imports/usda/mapper.py imports food_catalog.application.imports.usda.mapper",
}


class ArchitectureImportError(RuntimeError):
    pass


def _python_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _module_name_from_path(path: Path) -> str:
    return ".".join(path.relative_to(PROJECT_ROOT).with_suffix("").parts)


def _parse(path: Path) -> ast.AST:
    try:
        return ast.parse(path.read_text(), filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - failure message helper
        raise ArchitectureImportError(f"Could not parse {path}: {exc}") from exc


def _imports_from(path: Path) -> set[str]:
    tree = _parse(path)
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def _import_offenders(root: Path, forbidden_prefixes: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []

    for path in _python_files(root):
        imports = _imports_from(path)
        for imported in sorted(imports):
            if any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes):
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)} imports {imported}"
                )

    return offenders


def _django_http_imports(root: Path) -> list[str]:
    return _import_offenders(
        root,
        (
            "django.contrib.messages",
            "django.http",
            "django.shortcuts",
            "django.views",
            "django.urls",
        ),
    )


def _assert_no_new_imports(actual: list[str], allowed: set[str]) -> tuple[list[str], list[str]]:
    actual_set = set(actual)
    new_offenders = sorted(actual_set - allowed)
    resolved_allowlist_items = sorted(allowed - actual_set)
    return new_offenders, resolved_allowlist_items


class ArchitectureBoundaryTests(TestCase):
    def test_domain_layer_does_not_import_upper_layers(self):
        self.assertEqual(
            _import_offenders(
                DOMAIN_ROOT,
                (
                    "notas.application",
                    "notas.presentation",
                    "notas.interface",
                ),
            ),
            [],
        )

    def test_application_layer_does_not_import_presentation_or_interface(self):
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT,
                (
                    "notas.presentation",
                    "notas.interface",
                ),
            ),
            [],
        )

    def test_presentation_layer_does_not_import_interface(self):
        self.assertEqual(
            _import_offenders(
                PRESENTATION_ROOT,
                ("notas.interface",),
            ),
            [],
        )

    def test_mcp_package_does_not_import_django_app_layers_directly(self):
        self.assertEqual(
            _import_offenders(
                MCP_PACKAGE_ROOT,
                (
                    "django",
                    "notas",
                    "accounts",
                    "core",
                    "miapp",
                    "food_catalog",
                ),
            ),
            [],
        )

    def test_application_food_catalog_imports_are_limited_to_snapshot_protocol(self):
        new_offenders, resolved_allowlist_items = _assert_no_new_imports(
            _import_offenders(
                APPLICATION_ROOT,
                ("food_catalog",),
            ),
            APPLICATION_FOOD_CATALOG_IMPORT_ALLOWLIST,
        )

        self.assertEqual(
            new_offenders,
            [],
            msg=(
                "Application imports from food_catalog must stay limited to explicit "
                "compatibility bridges: operational snapshots, trusted backfill and legacy import wrappers."
            ),
        )
        self.assertEqual(
            resolved_allowlist_items,
            [],
            msg=(
                "A tolerated food_catalog import disappeared. Remove it from "
                "APPLICATION_FOOD_CATALOG_IMPORT_ALLOWLIST."
            ),
        )

    def test_application_django_http_imports_do_not_expand(self):
        new_offenders, resolved_allowlist_items = _assert_no_new_imports(
            _django_http_imports(APPLICATION_ROOT),
            APPLICATION_DJANGO_HTTP_IMPORT_ALLOWLIST,
        )

        self.assertEqual(
            new_offenders,
            [],
            msg=(
                "Application should not gain new HTTP/UI imports. "
                "Move request/render/url concerns to interface or presentation, "
                "or intentionally update the allowlist while documenting the bridge."
            ),
        )
        self.assertEqual(
            resolved_allowlist_items,
            [],
            msg=(
                "Some tolerated application HTTP imports disappeared. "
                "Remove them from APPLICATION_DJANGO_HTTP_IMPORT_ALLOWLIST."
            ),
        )

    def test_presentation_django_http_imports_do_not_expand(self):
        actual_imports = [
            item
            for item in _django_http_imports(PRESENTATION_ROOT)
            if not item.endswith(" imports django.urls")
        ]
        new_offenders, resolved_allowlist_items = _assert_no_new_imports(
            actual_imports,
            PRESENTATION_DJANGO_HTTP_IMPORT_ALLOWLIST,
        )

        self.assertEqual(
            new_offenders,
            [],
            msg=(
                "Presentation may build URLs, but should not gain new HTTP/view "
                "imports outside explicit page-level bridge modules."
            ),
        )
        self.assertEqual(
            resolved_allowlist_items,
            [],
            msg=(
                "Some tolerated presentation HTTP imports disappeared. "
                "Remove them from PRESENTATION_DJANGO_HTTP_IMPORT_ALLOWLIST."
            ),
        )

    def test_domain_layer_has_no_django_http_imports(self):
        self.assertEqual(_django_http_imports(DOMAIN_ROOT), [])

    def test_interface_layer_does_not_import_private_implementation_modules(self):
        self.assertEqual(
            _import_offenders(
                INTERFACE_ROOT,
                (
                    "mcp_server",
                    "notas.migrations",
                    "notas.tests",
                ),
            ),
            [],
        )

    def test_food_catalog_app_boundary_exists_with_master_models(self):
        self.assertTrue((FOOD_CATALOG_ROOT / "apps.py").exists())
        self.assertTrue((FOOD_CATALOG_ROOT / "models.py").exists())
        self.assertTrue((FOOD_CATALOG_ROOT / "migrations" / "__init__.py").exists())

        settings_text = SETTINGS_BASE.read_text()
        self.assertIn(
            '"food_catalog.apps.FoodCatalogConfig"',
            settings_text,
        )

        models_text = (FOOD_CATALOG_ROOT / "models.py").read_text()
        self.assertIn("class CatalogFood(models.Model):", models_text)
        self.assertIn("class CatalogFoodPortion(models.Model):", models_text)
        self.assertIn("class CatalogFoodAlias(models.Model):", models_text)
        self.assertIn("class CatalogFoodSource(models.Model):", models_text)
        self.assertIn("class CatalogImportBatch(models.Model):", models_text)
        self.assertNotIn("from notas", models_text)
        self.assertNotIn("import notas", models_text)
        self.assertNotIn("mcp_server", models_text)


    def test_food_catalog_app_does_not_import_operational_layers_or_mcp(self):
        self.assertEqual(
            _import_offenders(
                FOOD_CATALOG_ROOT,
                (
                    "notas",
                    "mcp_server",
                ),
            ),
            [],
        )

    def test_notas_package_keeps_expected_layer_directories(self):
        expected_layer_dirs = {
            "application",
            "domain",
            "interface",
            "presentation",
        }
        actual_layer_dirs = {
            path.name
            for path in NOTAS_ROOT.iterdir()
            if path.is_dir() and path.name in expected_layer_dirs
        }

        self.assertEqual(actual_layer_dirs, expected_layer_dirs)

    def test_root_urlconf_only_aggregates_feature_url_modules(self):
        text = ROOT_URLCONF.read_text()
        expected_includes = {
            "notas.interface.urls.admin_tools",
            "notas.interface.urls.ai_intake",
            "notas.interface.urls.ai_tools",
            "notas.interface.urls.comparators",
            "notas.interface.urls.dailyplans",
            "notas.interface.urls.elemental",
            "notas.interface.urls.foods",
            "notas.interface.urls.inbox",
            "notas.interface.urls.meals",
            "notas.interface.urls.profiles",
            "notas.interface.urls.programs",
            "notas.interface.urls.proposals",
            "notas.interface.urls.pwa",
        }

        for module in expected_includes:
            self.assertIn(f'include("{module}")', text)

        self.assertIn('path("", home_view, name="home_view")', text)
        self.assertNotIn('path("foods/', text)
        self.assertNotIn('path("meals/', text)
        self.assertNotIn('path("dailyplans/', text)
        self.assertNotIn('path("programs/', text)
        self.assertNotIn('path("comparators/', text)
        self.assertNotIn('path("inbox/', text)

    def test_each_feature_url_module_declares_urlpatterns(self):
        offenders = []

        for path in sorted(FEATURE_URLS_ROOT.glob("*.py")):
            if path.name == "__init__.py":
                continue
            text = path.read_text()
            if "urlpatterns" not in text:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))

        self.assertEqual(offenders, [])

    def test_application_services_keeps_commands_and_integrations_not_queries(self):
        legacy_queries_root = APPLICATION_ROOT / "services" / "queries"
        legacy_python_files = (
            _python_files(legacy_queries_root) if legacy_queries_root.exists() else []
        )

        self.assertEqual(
            legacy_python_files,
            [],
            msg=(
                "Read/query helpers belong in notas/application/queries/. "
                "Do not recreate Python modules in notas/application/services/queries/."
            ),
        )

    def test_production_code_does_not_import_legacy_services_queries(self):
        production_roots = (
            APPLICATION_ROOT,
            PRESENTATION_ROOT,
            INTERFACE_ROOT,
        )
        offenders: list[str] = []

        for root in production_roots:
            offenders.extend(
                _import_offenders(
                    root,
                    ("notas.application.services.queries",),
                )
            )

        self.assertEqual(offenders, [])

    def test_application_services_commands_do_not_import_views_or_templates(self):
        commands_root = APPLICATION_ROOT / "services" / "commands"
        self.assertEqual(
            _import_offenders(
                commands_root,
                (
                    "django.shortcuts",
                    "django.contrib.messages",
                    "django.template",
                    "notas.interface",
                    "notas.presentation",
                ),
            ),
            [],
        )

    def test_no_production_code_imports_test_modules(self):
        production_roots = (
            DOMAIN_ROOT,
            APPLICATION_ROOT,
            PRESENTATION_ROOT,
            INTERFACE_ROOT,
            MCP_PACKAGE_ROOT,
        )
        offenders: list[str] = []

        for root in production_roots:
            offenders.extend(
                _import_offenders(
                    root,
                    (
                        "notas.tests",
                        "mcp_server.tests",
                    ),
                )
            )

        self.assertEqual(offenders, [])

    def test_python_files_do_not_use_relative_imports_crossing_modules(self):
        offenders: list[str] = []

        for root in (DOMAIN_ROOT, APPLICATION_ROOT, PRESENTATION_ROOT, INTERFACE_ROOT):
            for path in _python_files(root):
                tree = _parse(path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.level > 1:
                        offenders.append(
                            f"{path.relative_to(PROJECT_ROOT)} uses relative import level {node.level}"
                        )

        self.assertEqual(offenders, [])
