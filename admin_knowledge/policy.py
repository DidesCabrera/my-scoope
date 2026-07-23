"""Non-authoritative, human-only governance for Admin Knowledge.

This module is intentionally declarative and dependency-free. Product features
must never import it. The Knowledge Center consumes an explicit allowlist so a
normal documentation or feature cycle cannot update the app indirectly.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeCenterPolicy:
    audience: str
    authoritative: bool
    codex_context_source: bool
    automatic_discovery: bool
    automatic_cycle_updates: bool
    requires_explicit_owner_request: bool
    product_dependencies_allowed: bool
    source_of_truth_label: str


POLICY = KnowledgeCenterPolicy(
    audience="human_staff",
    authoritative=False,
    codex_context_source=False,
    automatic_discovery=False,
    automatic_cycle_updates=False,
    requires_explicit_owner_request=True,
    product_dependencies_allowed=False,
    source_of_truth_label="Código, tests y documentación normativa aplicable",
)


KNOWLEDGE_DOCUMENT_PATHS = (
    "00_current/features/admin_knowledge/README.md",
    "00_current/features/admin_knowledge/ai_assistant.md",
    "00_current/features/admin_knowledge/food_catalog.md",
    "00_current/features/admin_knowledge/nutrition_solver.md",
)


HUMAN_REFERENCE_MARKERS = (
    "Role: human_reference",
    "Authority: non_authoritative",
    "Update-Policy: explicit_user_request_only",
)
