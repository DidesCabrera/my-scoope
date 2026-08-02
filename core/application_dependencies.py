"""Executable cross-app dependency policy.

This module records the current modular-monolith edges so new coupling cannot appear
silently. Removing an edge is encouraged, but the policy and its transition evidence
must be updated in the same patch.
"""

PROJECT_APPS = (
    "accounts",
    "admin_analytics",
    "admin_operations",
    "ai_assistant",
    "billing",
    "core",
    "email_delivery",
    "food_catalog",
    "notas",
    "nutrition_solver",
)

ALLOWED_APP_DEPENDENCIES = {
    "accounts": frozenset({"email_delivery", "notas"}),
    "admin_analytics": frozenset({"accounts", "ai_assistant", "food_catalog", "notas", "nutrition_solver"}),
    "admin_operations": frozenset({"accounts", "ai_assistant", "billing", "core", "food_catalog", "notas"}),
    "ai_assistant": frozenset({"accounts", "billing", "notas"}),
    "billing": frozenset({"accounts", "notas"}),
    "core": frozenset({"food_catalog", "notas"}),
    "email_delivery": frozenset(),
    "food_catalog": frozenset(),
    "notas": frozenset({"accounts", "ai_assistant", "core", "email_delivery", "food_catalog", "nutrition_solver"}),
    "nutrition_solver": frozenset(),
}

TRANSITIONAL_APP_EDGES = {
    ("accounts", "notas"): "Account forms/profile compatibility remains until notas.Profile ownership is retired.",
    ("notas", "accounts"): "Commercial entitlement resolution is moving from legacy notas plan fields to accounts.",
    ("ai_assistant", "notas"): "Product operations still enter notas through explicit tool/application adapters.",
    ("notas", "ai_assistant"): "Chat persistence and nutrition intake remain in notas during the runtime seam extraction.",
}

ADMIN_OPERATIONS_HTTP_IMPORT_ALLOWLIST = frozenset()
