"""Canonical contracts for assistant-visible client memory objects.

The provider context, tool schemas and product adapters must speak the same
field language.  Product-specific storage may map these names to legacy fields,
but it must not invent a second provider-facing vocabulary.
"""

from __future__ import annotations

PROFILE_DRAFT_FIELDS = (
    "weight_kg",
    "height_cm",
    "age_years",
    "sex",
    "activity_level",
    "training_frequency",
)

PREFERENCE_DRAFT_FIELDS = (
    "dietary_pattern",
    "avoided_foods",
    "preferred_foods",
    "allergies_or_intolerances",
    "preferred_meals_per_day",
    "cooking_time_preference",
    "budget_preference",
    "simplicity_preference",
    "variety_preference",
)

PROPOSAL_PREFERENCE_FIELDS = (
    "goal",
    "requested_entity",
    "meals_per_day",
    "complexity_level",
    "energy_adjustment",
    "calorie_target",
    "protein_target",
    "carb_target",
    "fat_target",
    "notes",
)

PERSISTENT_PREFERENCE_FIELDS = PREFERENCE_DRAFT_FIELDS

CLIENT_MEMORY_CONTRACT_VERSION = "ai_assistant_client_memory.v2"


__all__ = [
    "CLIENT_MEMORY_CONTRACT_VERSION",
    "PERSISTENT_PREFERENCE_FIELDS",
    "PREFERENCE_DRAFT_FIELDS",
    "PROFILE_DRAFT_FIELDS",
    "PROPOSAL_PREFERENCE_FIELDS",
]
