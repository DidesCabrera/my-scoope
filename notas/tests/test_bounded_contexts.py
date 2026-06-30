import ast
from pathlib import Path
from unittest import TestCase

from notas.application.bounded_contexts import (
    APPLICATION_BOUNDED_CONTEXTS,
    APPLICATION_CONTEXT_BY_PACKAGE,
    APPLICATION_CONTEXT_DEPENDENCY_POLICIES,
    APPLICATION_CONTEXT_POLICY_BY_SLUG,
    APPLICATION_SERVICE_AREAS,
    APPLICATION_SERVICE_AREA_BY_ENTRY,
    APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES,
    allowed_dependency_slugs_for_context,
    allowed_dependency_slugs_for_service_area,
    service_area_for_entry,
    service_area_for_import,
    context_for_application_import,
    context_for_application_package,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ROOT = PROJECT_ROOT / "notas" / "application"
SERVICES_ROOT = APPLICATION_ROOT / "services"


PRIVATE_OR_NON_CONTEXT_PACKAGES = {"__pycache__"}
SHARED_KERNEL_PACKAGES = {"dto", "resolvers", "validation"}
FEATURE_CONTEXT_PREFIXES = (
    "notas.application.ai_intake",
    "notas.application.ai_tools",
    "notas.application.nutrition_engine",
    "notas.application.proposals",
    "notas.application.queries",
    "notas.application.services",
    "notas.application.use_cases",
)


def _python_files(root: Path) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _imports_from(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    return imports




def _direct_service_entries() -> set[str]:
    entries: set[str] = set()

    for path in SERVICES_ROOT.iterdir():
        if (
            path.name == "__pycache__"
            or path.name == "__init__.py"
            or path.name.startswith("_")
        ):
            continue

        if path.is_file() and path.suffix == ".py":
            entries.add(path.stem)
            continue

        if path.is_dir() and any(child.suffix == ".py" for child in path.rglob("*.py")):
            entries.add(path.name)

    return entries


def _service_entry_from_path(path: Path) -> str:
    relative_parts = path.relative_to(SERVICES_ROOT).parts
    first_part = relative_parts[0]
    if first_part.endswith(".py"):
        return Path(first_part).stem
    return first_part


def _service_area_dependency_offenders() -> list[str]:
    offenders: list[str] = []

    for path in _python_files(SERVICES_ROOT):
        if path.name == "__init__.py":
            continue

        source_entry = _service_entry_from_path(path)
        source_area = service_area_for_entry(source_entry)
        if source_area is None:
            continue

        allowed_dependency_slugs = allowed_dependency_slugs_for_service_area(source_area.slug)
        for imported in sorted(_imports_from(path)):
            target_area = service_area_for_import(imported)
            if target_area is None or target_area.slug == source_area.slug:
                continue
            if target_area.slug not in allowed_dependency_slugs:
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)} [{source_area.slug}] "
                    f"imports {imported} [{target_area.slug}]"
                )

    return offenders


def _top_level_package(path: Path) -> str:
    return path.relative_to(APPLICATION_ROOT).parts[0]


def _context_dependency_offenders() -> list[str]:
    offenders: list[str] = []

    for path in _python_files(APPLICATION_ROOT):
        source_package = _top_level_package(path)
        source_context = context_for_application_package(source_package)
        if source_context is None:
            continue

        allowed_dependency_slugs = allowed_dependency_slugs_for_context(source_context.slug)
        for imported in sorted(_imports_from(path)):
            target_context = context_for_application_import(imported)
            if target_context is None or target_context.slug == source_context.slug:
                continue
            if target_context.slug not in allowed_dependency_slugs:
                offenders.append(
                    f"{path.relative_to(PROJECT_ROOT)} [{source_context.slug}] "
                    f"imports {imported} [{target_context.slug}]"
                )

    return offenders


def _import_offenders(root: Path, forbidden_prefixes: tuple[str, ...]) -> list[str]:
    offenders: list[str] = []

    for path in _python_files(root):
        for imported in sorted(_imports_from(path)):
            if any(
                imported == prefix or imported.startswith(f"{prefix}.")
                for prefix in forbidden_prefixes
            ):
                offenders.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

    return offenders


class ApplicationBoundedContextTests(TestCase):
    def test_context_slugs_are_unique(self):
        slugs = [context.slug for context in APPLICATION_BOUNDED_CONTEXTS]

        self.assertEqual(len(slugs), len(set(slugs)))

    def test_public_application_packages_are_assigned_to_one_context(self):
        actual_packages = {
            path.name
            for path in APPLICATION_ROOT.iterdir()
            if path.is_dir()
            and path.name not in PRIVATE_OR_NON_CONTEXT_PACKAGES
            and not path.name.startswith("_")
        }
        declared_packages = set(APPLICATION_CONTEXT_BY_PACKAGE)

        self.assertEqual(
            actual_packages - declared_packages,
            set(),
            msg="Every public notas/application package must belong to a bounded context.",
        )
        self.assertEqual(
            declared_packages - actual_packages,
            set(),
            msg="Bounded contexts should not reference missing application packages.",
        )

    def test_application_packages_are_not_declared_in_multiple_contexts(self):
        seen: dict[str, str] = {}
        duplicates: list[str] = []

        for context in APPLICATION_BOUNDED_CONTEXTS:
            for package in context.packages:
                if package in seen:
                    duplicates.append(f"{package}: {seen[package]} and {context.slug}")
                seen[package] = context.slug

        self.assertEqual(duplicates, [])

    def test_context_lookup_returns_expected_owner(self):
        self.assertEqual(context_for_application_package("ai_intake").slug, "ai_nutrition_flow")
        self.assertEqual(context_for_application_package("nutrition_engine").slug, "nutrition_engine")
        self.assertEqual(context_for_application_package("ai_tools").slug, "ai_integration")
        self.assertEqual(context_for_application_package("proposals").slug, "proposal_review")
        self.assertIsNone(context_for_application_package("does_not_exist"))

    def test_context_dependency_policies_cover_all_contexts(self):
        declared_context_slugs = {context.slug for context in APPLICATION_BOUNDED_CONTEXTS}
        policy_context_slugs = {policy.source_slug for policy in APPLICATION_CONTEXT_DEPENDENCY_POLICIES}

        self.assertEqual(policy_context_slugs, declared_context_slugs)

        unknown_policy_targets = {
            dependency_slug
            for policy in APPLICATION_CONTEXT_DEPENDENCY_POLICIES
            for dependency_slug in policy.allowed_dependency_slugs
            if dependency_slug not in declared_context_slugs
        }
        self.assertEqual(unknown_policy_targets, set())

    def test_context_dependency_policies_are_acyclic_for_shared_kernel(self):
        self.assertEqual(allowed_dependency_slugs_for_context("shared_kernel"), frozenset())
        self.assertEqual(
            APPLICATION_CONTEXT_POLICY_BY_SLUG["shared_kernel"].rationale,
            "Shared contracts stay dependency-light and cannot import feature contexts.",
        )

    def test_application_context_dependencies_do_not_expand_beyond_policy(self):
        self.assertEqual(
            _context_dependency_offenders(),
            [],
            msg=(
                "Application bounded contexts should only depend on explicitly "
                "allowed context directions from bounded_contexts.py."
            ),
        )

    def test_read_models_no_longer_depend_on_ai_nutrition_contexts(self):
        self.assertNotIn(
            "ai_nutrition_flow",
            allowed_dependency_slugs_for_context("read_models"),
        )
        self.assertNotIn(
            "nutrition_engine",
            allowed_dependency_slugs_for_context("read_models"),
        )
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT / "queries",
                ("notas.application.ai_intake", "notas.application.nutrition_engine"),
            ),
            [],
        )

    def test_shared_kernel_does_not_import_feature_contexts(self):
        offenders: list[str] = []

        for package in SHARED_KERNEL_PACKAGES:
            package_root = APPLICATION_ROOT / package
            if not package_root.exists():
                continue
            forbidden_prefixes = tuple(
                prefix
                for prefix in FEATURE_CONTEXT_PREFIXES
                if not prefix.startswith(f"notas.application.{package}")
            )
            offenders.extend(_import_offenders(package_root, forbidden_prefixes))

        self.assertEqual(
            offenders,
            [],
            msg="Shared kernel packages should not depend on feature contexts.",
        )


    def test_ai_nutrition_flow_is_distinct_from_engine_core(self):
        self.assertIn(
            "nutrition_engine",
            allowed_dependency_slugs_for_context("ai_nutrition_flow"),
        )
        self.assertEqual(
            allowed_dependency_slugs_for_context("nutrition_engine"),
            frozenset(),
        )
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT / "nutrition_engine",
                ("notas.application.ai_intake",),
            ),
            [],
            msg="The engine core must never import the conversational flow back.",
        )

    def test_ai_integration_depends_on_flow_not_engine_core(self):
        self.assertIn(
            "ai_nutrition_flow",
            allowed_dependency_slugs_for_context("ai_integration"),
        )
        self.assertNotIn(
            "nutrition_engine",
            allowed_dependency_slugs_for_context("ai_integration"),
        )

    def test_nutrition_engine_core_stays_independent_from_orchestrators(self):
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT / "nutrition_engine",
                (
                    "notas.application.ai_intake",
                    "notas.application.ai_tools",
                    "notas.application.proposals",
                    "notas.application.queries",
                    "notas.application.services",
                    "notas.interface",
                    "notas.presentation",
                ),
            ),
            [],
        )

    def test_ai_tools_do_not_import_nutrition_engine_directly(self):
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT / "ai_tools",
                ("notas.application.nutrition_engine",),
            ),
            [],
            msg=(
                "MCP/API tools should enter the nutrition flow through ai_intake "
                "use cases, not through engine internals."
            ),
        )

    def test_proposal_review_does_not_depend_on_ai_integration_or_chat_flow(self):
        self.assertEqual(
            _import_offenders(
                APPLICATION_ROOT / "proposals",
                (
                    "notas.application.ai_tools",
                    "notas.application.ai_intake",
                ),
            ),
            [],
        )

    def test_domain_service_entries_are_assigned_to_one_service_area(self):
        actual_entries = _direct_service_entries()
        declared_entries = set(APPLICATION_SERVICE_AREA_BY_ENTRY)

        self.assertEqual(
            actual_entries - declared_entries,
            set(),
            msg="Every direct notas/application/services entry must belong to a service area.",
        )
        self.assertEqual(
            declared_entries - actual_entries,
            set(),
            msg="Service areas should not reference missing services entries.",
        )

    def test_service_area_entries_are_not_declared_twice(self):
        seen: dict[str, str] = {}
        duplicates: list[str] = []

        for area in APPLICATION_SERVICE_AREAS:
            for entry in area.entries:
                if entry in seen:
                    duplicates.append(f"{entry}: {seen[entry]} and {area.slug}")
                seen[entry] = area.slug

        self.assertEqual(duplicates, [])

    def test_service_area_lookup_returns_expected_owner(self):
        self.assertEqual(service_area_for_entry("commands").slug, "commands")
        self.assertEqual(service_area_for_entry("food_imports").slug, "food_catalog")
        self.assertEqual(service_area_for_entry("nutrition").slug, "nutrition_services")
        self.assertEqual(service_area_for_entry("mcp_user_tokens").slug, "auth_integration")
        self.assertIsNone(service_area_for_entry("does_not_exist"))

    def test_service_area_dependency_policies_cover_all_service_areas(self):
        declared_service_slugs = {area.slug for area in APPLICATION_SERVICE_AREAS}
        policy_service_slugs = {policy.source_slug for policy in APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES}

        self.assertEqual(policy_service_slugs, declared_service_slugs)

        unknown_policy_targets = {
            dependency_slug
            for policy in APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES
            for dependency_slug in policy.allowed_dependency_slugs
            if dependency_slug not in declared_service_slugs
        }
        self.assertEqual(unknown_policy_targets, set())

    def test_domain_service_area_dependencies_do_not_expand_beyond_policy(self):
        self.assertEqual(
            _service_area_dependency_offenders(),
            [],
            msg=(
                "Domain-service areas should only depend on explicitly allowed "
                "service-area directions from bounded_contexts.py."
            ),
        )

    def test_auth_integration_stays_isolated_from_feature_service_areas(self):
        self.assertEqual(allowed_dependency_slugs_for_service_area("auth_integration"), frozenset())

        offenders: list[str] = []
        forbidden_prefixes = (
            "notas.application.services.commands",
            "notas.application.services.comparisons",
            "notas.application.services.food_imports",
            "notas.application.services.nutrition",
        )
        for path in _python_files(SERVICES_ROOT):
            if _service_entry_from_path(path) not in {"mcp_user_tokens", "oauth_authorization_codes"}:
                continue
            for imported in sorted(_imports_from(path)):
                if any(
                    imported == prefix or imported.startswith(f"{prefix}.")
                    for prefix in forbidden_prefixes
                ):
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} imports {imported}")

        self.assertEqual(offenders, [])

