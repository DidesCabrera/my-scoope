"""Versioned, reviewed food copy for the existing operational detail surface.

Editorial text is independent of nutrition snapshots. Production legacy records
without a master catalog identity are bound to both their operational ID and name.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "food_descriptions_v1.json"
_VISIBLE_STATES = {"approved", "approved_with_limitations"}


@lru_cache(maxsize=1)
def _description_maps() -> tuple[dict[str, dict], dict[int, dict]]:
    payload = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    if payload["schema_version"] != "myscoope.food_descriptions.v1":
        raise ValueError("Unsupported food description dataset version")

    catalog: dict[str, dict] = {}
    legacy: dict[int, dict] = {}
    for record in payload["records"]:
        if record["review_state"] not in _VISIBLE_STATES:
            continue
        if "catalog_ref" in record:
            key = record["catalog_ref"]
            if key in catalog:
                raise ValueError(f"Duplicate catalog food description: {key}")
            catalog[key] = record
        else:
            key = record["operational_food_id"]
            if key in legacy:
                raise ValueError(f"Duplicate legacy food description: {key}")
            legacy[key] = record
    return catalog, legacy


def description_for_food(food) -> str:
    """Return reviewed copy only for its exact active global food identity."""
    if not food.is_global or not food.is_active:
        return ""
    catalog, legacy = _description_maps()
    if food.catalog_food_ref is not None:
        record = catalog.get(str(food.catalog_food_ref))
    else:
        record = legacy.get(food.id)
    if record is None or record["name"] != food.name:
        return ""
    return record["description"]
