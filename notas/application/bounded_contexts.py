"""Explicit bounded-context map for the application layer.

This module is intentionally small and dependency-free.  It gives tests,
documentation and future refactors a single place to answer:

* which part of the application owns this package?
* which bounded contexts may depend on which other bounded contexts?
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationBoundedContext:
    """Application-level bounded context declaration.

    ``packages`` are top-level packages below ``notas.application``.  They are
    deliberately coarse-grained: the goal is to make ownership and dependency
    direction visible before splitting anything into separate Django apps.
    """

    slug: str
    label: str
    packages: tuple[str, ...]
    responsibility: str




@dataclass(frozen=True)
class ApplicationServiceArea:
    """Explicit ownership declaration for modules inside domain_services.

    ``entries`` are direct children below ``notas.application.services``.  They
    may be package directories such as ``commands`` or single modules such as
    ``mcp_user_tokens``.  This keeps the broad ``domain_services`` context from
    becoming an ambiguous catch-all.
    """

    slug: str
    label: str
    entries: tuple[str, ...]
    responsibility: str


@dataclass(frozen=True)
class ApplicationServiceAreaDependencyPolicy:
    """Allowed dependency direction between service areas."""

    source_slug: str
    allowed_dependency_slugs: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class ApplicationContextDependencyPolicy:
    """Allowed dependency direction between application bounded contexts."""

    source_slug: str
    allowed_dependency_slugs: tuple[str, ...]
    rationale: str


APPLICATION_BOUNDED_CONTEXTS: tuple[ApplicationBoundedContext, ...] = (
    ApplicationBoundedContext(
        slug="shared_kernel",
        label="Shared Kernel",
        packages=("dto", "resolvers", "validation"),
        responsibility=(
            "Stable DTOs, validators and small resolvers shared by several "
            "application contexts. This context must stay dependency-light."
        ),
    ),
    ApplicationBoundedContext(
        slug="read_models",
        label="Read Models",
        packages=("queries",),
        responsibility=(
            "Optimized reads, querysets, projections and prefetch helpers used "
            "by interface, presentation and application services."
        ),
    ),
    ApplicationBoundedContext(
        slug="domain_services",
        label="Domain Services",
        packages=("services", "use_cases"),
        responsibility=(
            "Commands, integrations, cache builders, access helpers, imports "
            "and service-level operations that coordinate domain models."
        ),
    ),
    ApplicationBoundedContext(
        slug="nutrition_engine",
        label="Nutrition Engine",
        packages=("nutrition_engine",),
        responsibility=(
            "Deterministic nutrition-engine core: target estimation, meal "
            "templates, portion solving, candidate selection and strict validation."
        ),
    ),
    ApplicationBoundedContext(
        slug="ai_nutrition_flow",
        label="AI Nutrition Flow",
        packages=("ai_intake",),
        responsibility=(
            "Conversational nutrition brief, chat history, plan-generation "
            "use cases and proposal iteration orchestration."
        ),
    ),
    ApplicationBoundedContext(
        slug="ai_integration",
        label="AI Integration",
        packages=("ai_tools",),
        responsibility=(
            "Internal contracts exposed to API/MCP adapters. This context "
            "orchestrates safe tools without owning nutrition-engine rules."
        ),
    ),
    ApplicationBoundedContext(
        slug="proposal_review",
        label="Proposal Review",
        packages=("proposals",),
        responsibility=(
            "Proposal contracts, validators and applicators for the explicit "
            "review/approve/apply flow."
        ),
    ),
)


APPLICATION_SERVICE_AREAS: tuple[ApplicationServiceArea, ...] = (
    ApplicationServiceArea(
        slug="access",
        label="Access",
        entries=("access",),
        responsibility="Capability and ownership helpers used by interface/application boundaries.",
    ),
    ApplicationServiceArea(
        slug="cache",
        label="Cache Builders",
        entries=("cache",),
        responsibility="Derived nutrition/program summaries and cached projections.",
    ),
    ApplicationServiceArea(
        slug="commands",
        label="Entity Commands",
        entries=("commands",),
        responsibility="Write-side operations for foods, meals, daily plans, programs, calendarization, sharing and proposals.",
    ),
    ApplicationServiceArea(
        slug="comparisons",
        label="Comparisons",
        entries=("comparisons",),
        responsibility="Saved-comparison payloads, snapshots and nutrition comparison helpers.",
    ),
    ApplicationServiceArea(
        slug="food_catalog",
        label="Food Catalog",
        entries=("food_imports", "food_catalog_snapshots"),
        responsibility=(
            "Core-food catalog, import normalization, USDA mapping, "
            "snapshot publication helpers and visibility policy."
        ),
    ),
    ApplicationServiceArea(
        slug="notifications",
        label="Notifications",
        entries=("notifications",),
        responsibility="Outbound message builders and notification content.",
    ),
    ApplicationServiceArea(
        slug="scheduling",
        label="Scheduling",
        entries=("calendarization",),
        responsibility="Calendarization snapshots, timezone conversion and reusable scheduling rules.",
    ),
    ApplicationServiceArea(
        slug="nutrition_services",
        label="Nutrition Services",
        entries=("nutrition",),
        responsibility="Reusable nutrition aggregation, meal totals, KPI and weight helpers.",
    ),
    ApplicationServiceArea(
        slug="auth_integration",
        label="Auth Integration",
        entries=(
            "mcp_user_tokens",
            "oauth_authorization_codes",
            "oauth_device_sessions",
        ),
        responsibility=(
            "MCP and mobile access tokens, OAuth authorization codes, and "
            "durable device-session lifecycle services."
        ),
    ),
)


APPLICATION_SERVICE_AREA_BY_ENTRY: dict[str, ApplicationServiceArea] = {
    entry: area
    for area in APPLICATION_SERVICE_AREAS
    for entry in area.entries
}


APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES: tuple[ApplicationServiceAreaDependencyPolicy, ...] = (
    ApplicationServiceAreaDependencyPolicy(
        source_slug="access",
        allowed_dependency_slugs=(),
        rationale="Access helpers may depend on read models, but should not import other service areas.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="cache",
        allowed_dependency_slugs=("food_catalog",),
        rationale="Cache builders may reuse food-catalog display normalization helpers.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="commands",
        allowed_dependency_slugs=(
            "cache",
            "comparisons",
            "food_catalog",
            "notifications",
            "nutrition_services",
            "scheduling",
        ),
        rationale="Commands coordinate lower-level services while remaining the write-side entrypoint.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="comparisons",
        allowed_dependency_slugs=(),
        rationale="Comparison helpers stay self-contained under the commands that persist them.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="food_catalog",
        allowed_dependency_slugs=(),
        rationale="Food-catalog import helpers are a low-level service area.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="notifications",
        allowed_dependency_slugs=(),
        rationale="Notification builders should not coordinate business service areas.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="scheduling",
        allowed_dependency_slugs=(),
        rationale="Scheduling helpers stay deterministic and are coordinated by commands.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="nutrition_services",
        allowed_dependency_slugs=("food_catalog",),
        rationale="Nutrition aggregation may reuse food display normalization helpers.",
    ),
    ApplicationServiceAreaDependencyPolicy(
        source_slug="auth_integration",
        allowed_dependency_slugs=(),
        rationale="OAuth/MCP token services stay isolated from feature service areas.",
    ),
)


APPLICATION_SERVICE_AREA_POLICY_BY_SLUG: dict[str, ApplicationServiceAreaDependencyPolicy] = {
    policy.source_slug: policy
    for policy in APPLICATION_SERVICE_AREA_DEPENDENCY_POLICIES
}


APPLICATION_CONTEXT_BY_PACKAGE: dict[str, ApplicationBoundedContext] = {
    package: context
    for context in APPLICATION_BOUNDED_CONTEXTS
    for package in context.packages
}


APPLICATION_CONTEXT_DEPENDENCY_POLICIES: tuple[ApplicationContextDependencyPolicy, ...] = (
    ApplicationContextDependencyPolicy(
        source_slug="shared_kernel",
        allowed_dependency_slugs=(),
        rationale="Shared contracts stay dependency-light and cannot import feature contexts.",
    ),
    ApplicationContextDependencyPolicy(
        source_slug="read_models",
        allowed_dependency_slugs=("shared_kernel", "read_models", "domain_services"),
        rationale=(
            "Read models may use DTOs/validators and existing nutrition/food "
            "helpers, but should not depend on feature orchestrators such as "
            "AI chat or MCP tools."
        ),
    ),
    ApplicationContextDependencyPolicy(
        source_slug="domain_services",
        allowed_dependency_slugs=("shared_kernel", "read_models", "proposal_review"),
        rationale=(
            "Commands and services may coordinate shared contracts, optimized "
            "reads and proposal applicators."
        ),
    ),
    ApplicationContextDependencyPolicy(
        source_slug="nutrition_engine",
        allowed_dependency_slugs=(),
        rationale=(
            "The engine core stays deterministic and dependency-light. It must "
            "not import Django read models, services, proposal review or AI tools."
        ),
    ),
    ApplicationContextDependencyPolicy(
        source_slug="ai_nutrition_flow",
        allowed_dependency_slugs=(
            "shared_kernel",
            "read_models",
            "domain_services",
            "nutrition_engine",
        ),
        rationale=(
            "The conversational nutrition flow may read user/nutrition context, "
            "reuse commands/services and call the engine through explicit use "
            "cases, while the engine never imports the flow back."
        ),
    ),
    ApplicationContextDependencyPolicy(
        source_slug="ai_integration",
        allowed_dependency_slugs=(
            "shared_kernel",
            "read_models",
            "domain_services",
            "ai_nutrition_flow",
            "proposal_review",
        ),
        rationale=(
            "API/MCP application tools orchestrate safe read/write/use-case "
            "entrypoints, including reviewable proposal creation, without being imported by business contexts."
        ),
    ),
    ApplicationContextDependencyPolicy(
        source_slug="proposal_review",
        allowed_dependency_slugs=("shared_kernel", "read_models", "domain_services"),
        rationale=(
            "Proposal review can reuse stable payload contracts, read models and entity "
            "creation commands while staying independent from AI chat orchestration."
        ),
    ),
)


APPLICATION_CONTEXT_POLICY_BY_SLUG: dict[str, ApplicationContextDependencyPolicy] = {
    policy.source_slug: policy
    for policy in APPLICATION_CONTEXT_DEPENDENCY_POLICIES
}


def context_for_application_package(package_name: str) -> ApplicationBoundedContext | None:
    """Return the bounded context that owns a top-level application package."""

    return APPLICATION_CONTEXT_BY_PACKAGE.get(package_name)


def package_from_application_import(import_path: str) -> str | None:
    """Return the top-level ``notas.application`` package from an import path."""

    prefix = "notas.application."
    if not import_path.startswith(prefix):
        return None

    remainder = import_path.removeprefix(prefix)
    package_name = remainder.split(".", 1)[0]
    return package_name or None


def context_for_application_import(import_path: str) -> ApplicationBoundedContext | None:
    """Return the bounded context targeted by an application import path."""

    package_name = package_from_application_import(import_path)
    if package_name is None:
        return None

    return context_for_application_package(package_name)


def allowed_dependency_slugs_for_context(source_slug: str) -> frozenset[str]:
    """Return allowed dependency context slugs for ``source_slug``."""

    policy = APPLICATION_CONTEXT_POLICY_BY_SLUG.get(source_slug)
    if policy is None:
        return frozenset()

    return frozenset(policy.allowed_dependency_slugs)


def service_area_for_entry(entry_name: str) -> ApplicationServiceArea | None:
    """Return the service area that owns a direct child of application/services."""

    return APPLICATION_SERVICE_AREA_BY_ENTRY.get(entry_name)


def entry_from_service_import(import_path: str) -> str | None:
    """Return the direct ``notas.application.services`` entry from an import path."""

    prefix = "notas.application.services."
    if not import_path.startswith(prefix):
        return None

    remainder = import_path.removeprefix(prefix)
    entry_name = remainder.split(".", 1)[0]
    return entry_name or None


def service_area_for_import(import_path: str) -> ApplicationServiceArea | None:
    """Return the service area targeted by a services import path."""

    entry_name = entry_from_service_import(import_path)
    if entry_name is None:
        return None

    return service_area_for_entry(entry_name)


def allowed_dependency_slugs_for_service_area(source_slug: str) -> frozenset[str]:
    """Return allowed service-area dependency slugs for ``source_slug``."""

    policy = APPLICATION_SERVICE_AREA_POLICY_BY_SLUG.get(source_slug)
    if policy is None:
        return frozenset()

    return frozenset(policy.allowed_dependency_slugs)
