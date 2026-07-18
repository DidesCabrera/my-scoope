"""Source-agnostic contracts for Food Catalog import pipelines.

These DTOs describe external food rows before they are curated into the master
catalog or materialized later as operational ``notas.Food`` snapshots. They are
plain Python contracts and intentionally do not import Django models, ``notas``
or MCP modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ImportedFoodDTO:
    """Normalized external food record used by import adapters.

    The DTO is not an operational food and does not imply that a row is visible
    to Meals, Solver or MCP. Persistence and operational availability remain
    controlled by explicit backend protocols.
    """

    source: str
    source_food_id: str
    source_dataset: str
    source_version: str

    name: str
    canonical_name: str

    protein: Decimal
    carbs: Decimal
    fat: Decimal
    calories_kcal_per_100g: Decimal | None = None

    food_group: str = ""
    food_subgroup: str = ""
    preparation_state: str = "unknown"

    fiber_g_per_100g: Decimal | None = None
    sugar_g_per_100g: Decimal | None = None
    saturated_fat_g_per_100g: Decimal | None = None
    sodium_mg_per_100g: Decimal | None = None

    license_name: str = ""
    attribution: str = ""
    source_url: str = ""
    raw_payload_hash: str = ""
    normalized_payload_hash: str = ""
    source_description: str = ""
    source_data_type: str = ""


__all__ = ["ImportedFoodDTO"]
