import ast
from pathlib import Path
from unittest import TestCase


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ROOT = PROJECT_ROOT / "notas" / "application"
PRESENTATION_ROOT = PROJECT_ROOT / "notas" / "presentation"
ROOT_URLCONF = PROJECT_ROOT / "notas" / "urls.py"
FEATURE_URLS_ROOT = PROJECT_ROOT / "notas" / "interface" / "urls"


def _imports_from(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
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

    for path in sorted(root.rglob("*.py")):
        imports = _imports_from(path)
        for imported in sorted(imports):
            if any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes):
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)} imports {imported}"
                )

    return offenders


class ArchitectureBoundaryTests(TestCase):
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

    def test_root_urlconf_only_aggregates_feature_url_modules(self):
        text = ROOT_URLCONF.read_text()
        expected_includes = {
            "notas.interface.urls.admin_tools",
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
