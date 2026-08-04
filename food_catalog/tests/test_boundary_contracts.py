import ast
from pathlib import Path
from unittest import TestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FOOD_CATALOG_ROOT = PROJECT_ROOT / "food_catalog"
APPLICATION_ROOT = FOOD_CATALOG_ROOT / "application"
INFRASTRUCTURE_ROOT = FOOD_CATALOG_ROOT / "infrastructure"
MANAGEMENT_ROOT = FOOD_CATALOG_ROOT / "management"
MODELS_PATH = FOOD_CATALOG_ROOT / "models.py"


FORBIDDEN_OPERATIONAL_PREFIXES = (
    "notas",
    "mcp_server",
)

FORBIDDEN_APPLICATION_PREFIXES = (
    "django",
    *FORBIDDEN_OPERATIONAL_PREFIXES,
)

FORBIDDEN_MCP_IDENTIFIERS = (
    "@server.tool",
    "FastMCP",
    "dispatch_tool_call",
    "list_food_catalog",
)

FORBIDDEN_OPERATIONAL_MODEL_IDENTIFIERS = (
    "notas.Food",
    "MealFood",
    "DailyPlan",
    "ProgramDay",
    "NutritionProposal",
)


def _python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []

    return [
        path
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(), filename=str(path))


def _imports_from(path: Path) -> set[str]:
    tree = _parse(path)
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports


def _import_offenders(root: Path, forbidden_prefixes: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []

    for path in _python_files(root):
        for imported in sorted(_imports_from(path)):
            if any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

    return offenders


class FoodCatalogBoundaryContractTests(TestCase):
    def test_application_layer_stays_pure_and_operational_free(self):
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT,
                FORBIDDEN_APPLICATION_PREFIXES,
            ),
            [],
            msg=(
                "food_catalog.application must stay pure: no Django ORM, no notas, "
                "and no MCP imports. It owns contracts/adapters, not persistence or planning."
            ),
        )

    def test_infrastructure_does_not_import_operational_app_or_mcp(self):
        self.assertEqual(
            _import_offenders(
                INFRASTRUCTURE_ROOT,
                FORBIDDEN_OPERATIONAL_PREFIXES,
            ),
            [],
            msg=(
                "food_catalog.infrastructure may persist master catalog rows, but it must "
                "not read notas.Food or expose MCP behavior."
            ),
        )

    def test_management_commands_do_not_import_operational_app_or_mcp(self):
        self.assertEqual(
            _import_offenders(
                MANAGEMENT_ROOT,
                FORBIDDEN_OPERATIONAL_PREFIXES,
            ),
            [],
            msg=(
                "Food Catalog management commands are catalog-first commands. "
                "Operational bridges that read notas.Food must live in notas."
            ),
        )

    def test_master_catalog_models_do_not_import_operational_entities(self):
        offenders = _import_offenders(
            FOOD_CATALOG_ROOT,
            FORBIDDEN_OPERATIONAL_PREFIXES,
        )

        self.assertEqual(
            offenders,
            [],
            msg=(
                "food_catalog.models and modules must model the master catalog only. "
                "Operational entities must keep depending on notas.Food snapshots instead."
            ),
        )

    def test_food_catalog_python_modules_do_not_define_mcp_tools(self):
        offenders: list[str] = []
        scanned_roots = (
            FOOD_CATALOG_ROOT / "application",
            FOOD_CATALOG_ROOT / "infrastructure",
            FOOD_CATALOG_ROOT / "management",
            FOOD_CATALOG_ROOT / "models.py",
            FOOD_CATALOG_ROOT / "admin.py",
        )

        scanned_files: list[Path] = []
        for root in scanned_roots:
            if root.is_file():
                scanned_files.append(root)
            else:
                scanned_files.extend(_python_files(root))

        for path in scanned_files:
            source = path.read_text()
            for identifier in FORBIDDEN_MCP_IDENTIFIERS:
                if identifier in source:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {identifier}")

        self.assertEqual(
            offenders,
            [],
            msg="Food Catalog must not define or register MCP tools.",
        )
