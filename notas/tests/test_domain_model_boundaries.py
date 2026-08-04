import ast
import importlib
from pathlib import Path
from unittest import TestCase

from notas.domain.model_boundaries import (
    DOMAIN_MODEL_BOUNDARIES,
    DOMAIN_MODEL_BOUNDARY_BY_MODEL,
    DOMAIN_MODEL_DEPENDENCY_POLICIES,
    DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG,
    DOMAIN_MODEL_POLICY_BY_SLUG,
    allowed_dependency_slugs_for_model_boundary,
    boundary_for_model,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS_PATH = PROJECT_ROOT / "notas" / "domain" / "models.py"
MODEL_MODULES_DIR = PROJECT_ROOT / "notas" / "domain" / "model_modules"
IGNORED_EXTERNAL_MODEL_REFERENCES = {"User", "self"}
RELATION_FIELD_NAMES = {"ForeignKey", "OneToOneField", "ManyToManyField"}


def _model_source_paths() -> tuple[Path, ...]:
    module_paths = tuple(sorted(MODEL_MODULES_DIR.glob("*.py"))) if MODEL_MODULES_DIR.exists() else ()
    return (MODELS_PATH, *[path for path in module_paths if path.name != "__init__.py"])


def _parse_model_sources() -> tuple[tuple[Path, ast.AST], ...]:
    return tuple(
        (path, ast.parse(path.read_text(), filename=str(path)))
        for path in _model_source_paths()
    )


def _is_django_model_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Attribute) and base.attr == "Model":
            return True
        if isinstance(base, ast.Name) and base.id == "Model":
            return True
    for child in node.body:
        if not isinstance(child, ast.ClassDef) or child.name != "Meta":
            continue
        for statement in child.body:
            if (
                isinstance(statement, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "proxy" for target in statement.targets)
                and isinstance(statement.value, ast.Constant)
                and statement.value.value is True
            ):
                return True
    return False


def _concrete_model_class_names() -> set[str]:
    return {
        node.name
        for _, tree in _parse_model_sources()
        for node in tree.body
        if isinstance(node, ast.ClassDef) and _is_django_model_class(node)
    }


def _relation_target_name(arg: ast.AST) -> str | None:
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value.split(".")[-1]
    return None


def _model_references() -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []

    for _, tree in _parse_model_sources():
        for node in tree.body:
            if not isinstance(node, ast.ClassDef) or not _is_django_model_class(node):
                continue

            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue

                field_name: str | None = None
                if isinstance(child.func, ast.Attribute):
                    field_name = child.func.attr
                elif isinstance(child.func, ast.Name):
                    field_name = child.func.id

                if field_name not in RELATION_FIELD_NAMES or not child.args:
                    continue

                target = _relation_target_name(child.args[0])
                if target and target not in IGNORED_EXTERNAL_MODEL_REFERENCES:
                    references.append((node.name, target))

    return references


class DomainModelBoundaryTests(TestCase):
    def test_boundary_slugs_are_unique(self):
        slugs = [boundary.slug for boundary in DOMAIN_MODEL_BOUNDARIES]

        self.assertEqual(len(slugs), len(set(slugs)))

    def test_every_model_in_models_py_is_assigned_to_one_boundary(self):
        actual_models = _concrete_model_class_names()
        declared_models = set(DOMAIN_MODEL_BOUNDARY_BY_MODEL)

        self.assertEqual(
            actual_models - declared_models,
            set(),
            msg="Every Django model class in notas/domain/models.py must belong to a domain boundary.",
        )
        self.assertEqual(
            declared_models - actual_models,
            set(),
            msg="Domain model boundaries should not reference missing model classes.",
        )

    def test_models_are_not_declared_in_multiple_boundaries(self):
        seen: dict[str, str] = {}
        duplicates: list[str] = []

        for boundary in DOMAIN_MODEL_BOUNDARIES:
            for model_name in boundary.models:
                if model_name in seen:
                    duplicates.append(f"{model_name}: {seen[model_name]} and {boundary.slug}")
                seen[model_name] = boundary.slug

        self.assertEqual(duplicates, [])

    def test_boundary_lookup_returns_expected_owner(self):
        self.assertEqual(boundary_for_model("Food").slug, "food_catalog")
        self.assertEqual(boundary_for_model("Meal").slug, "meals")
        self.assertEqual(boundary_for_model("DailyPlan").slug, "dailyplans")
        self.assertEqual(boundary_for_model("Program").slug, "programs")
        self.assertEqual(boundary_for_model("NutritionProposal").slug, "proposals")
        self.assertEqual(boundary_for_model("SavedComparison").slug, "comparisons")
        self.assertIsNone(boundary_for_model("DoesNotExist"))

    def test_dependency_policies_cover_all_boundaries(self):
        declared_boundary_slugs = {boundary.slug for boundary in DOMAIN_MODEL_BOUNDARIES}
        policy_boundary_slugs = {policy.source_slug for policy in DOMAIN_MODEL_DEPENDENCY_POLICIES}

        self.assertEqual(policy_boundary_slugs, declared_boundary_slugs)

        unknown_policy_targets = {
            dependency_slug
            for policy in DOMAIN_MODEL_DEPENDENCY_POLICIES
            for dependency_slug in policy.allowed_dependency_slugs
            if dependency_slug not in declared_boundary_slugs
        }
        self.assertEqual(unknown_policy_targets, set())

    def test_foundational_model_boundaries_stay_dependency_light(self):
        self.assertEqual(allowed_dependency_slugs_for_model_boundary("identity"), frozenset())
        self.assertEqual(allowed_dependency_slugs_for_model_boundary("auth_integration"), frozenset())
        self.assertEqual(allowed_dependency_slugs_for_model_boundary("food_catalog"), frozenset())

    def test_model_relations_do_not_expand_beyond_boundary_policy(self):
        offenders: list[str] = []

        for source_model, target_model in _model_references():
            source_boundary = boundary_for_model(source_model)
            target_boundary = boundary_for_model(target_model)
            if source_boundary is None or target_boundary is None:
                offenders.append(f"{source_model} references unassigned model {target_model}")
                continue
            if source_boundary.slug == target_boundary.slug:
                continue
            allowed_dependencies = allowed_dependency_slugs_for_model_boundary(source_boundary.slug)
            if target_boundary.slug not in allowed_dependencies:
                offenders.append(
                    f"{source_model} [{source_boundary.slug}] references "
                    f"{target_model} [{target_boundary.slug}]"
                )

        self.assertEqual(
            offenders,
            [],
            msg=(
                "Domain model relations should only cross boundaries through "
                "explicit DOMAIN_MODEL_DEPENDENCY_POLICIES."
            ),
        )

    def test_policy_lookup_is_complete_for_declared_boundaries(self):
        for boundary in DOMAIN_MODEL_BOUNDARIES:
            self.assertIn(boundary.slug, DOMAIN_MODEL_POLICY_BY_SLUG)


    def test_expected_boundaries_are_physically_split(self):
        self.assertEqual(
            DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG,
            {
                "identity": "notas.domain.model_modules.identity",
                "auth_integration": "notas.domain.model_modules.auth_integration",
                "sharing": "notas.domain.model_modules.sharing",
                "comparisons": "notas.domain.model_modules.comparisons",
                "proposals": "notas.domain.model_modules.proposals",
                "calendarization": "notas.domain.model_modules.calendarization",
                "notification_delivery": "notas.domain.model_modules.notification_delivery",
                "food_catalog": "notas.domain.model_modules.food",
                "meals": "notas.domain.model_modules.meals",
                "dailyplans": "notas.domain.model_modules.dailyplans",
                "programs": "notas.domain.model_modules.programs",
            },
        )

    def test_compatibility_facade_contains_no_concrete_model_definitions(self):
        tree = ast.parse(MODELS_PATH.read_text(), filename=str(MODELS_PATH))
        concrete = [
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef) and _is_django_model_class(node)
        ]
        self.assertEqual(concrete, [])
        self.assertLessEqual(len(MODELS_PATH.read_text().splitlines()), 120)

    def test_declared_physical_model_modules_are_importable(self):
        for boundary_slug, module_path in DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG.items():
            with self.subTest(boundary=boundary_slug):
                module = importlib.import_module(module_path)
                boundary = next(
                    boundary
                    for boundary in DOMAIN_MODEL_BOUNDARIES
                    if boundary.slug == boundary_slug
                )
                for model_name in boundary.models:
                    self.assertTrue(
                        hasattr(module, model_name),
                        msg=f"{module_path} should export {model_name}.",
                    )

    def test_split_models_remain_available_from_compatibility_module(self):
        compatibility_module = importlib.import_module("notas.domain.models")

        for boundary_slug in DOMAIN_MODEL_MODULE_BY_BOUNDARY_SLUG:
            boundary = next(
                boundary
                for boundary in DOMAIN_MODEL_BOUNDARIES
                if boundary.slug == boundary_slug
            )
            for model_name in boundary.models:
                with self.subTest(model=model_name):
                    self.assertTrue(hasattr(compatibility_module, model_name))
