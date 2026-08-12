"""Versioned orientation profiles for Codex-assisted portion decisions.

Profiles constrain and explain proposals; they are not universal formulas and
do not replace a food-level decision.
"""

ENRICHMENT_PROFILE_VERSION = "catalog-portion-profiles.cl.v1"

PORTION_PROFILES = {
    "cooked_legume": {"min_g": [40, 100], "max_g": [180, 350], "step_g": [5, 20]},
    "cooked_cereal": {"min_g": [40, 100], "max_g": [180, 350], "step_g": [5, 20]},
    "dry_cereal": {"min_g": [15, 50], "max_g": [60, 150], "step_g": [5, 10]},
    "cooked_animal_protein": {"min_g": [40, 100], "max_g": [180, 350], "step_g": [5, 20]},
    "raw_animal_protein": {"min_g": [50, 120], "max_g": [200, 400], "step_g": [5, 20]},
    "low_density_vegetable": {"min_g": [20, 100], "max_g": [150, 500], "step_g": [5, 25]},
    "cooked_tuber": {"min_g": [50, 120], "max_g": [200, 450], "step_g": [5, 25]},
    "fruit_by_weight": {"min_g": [40, 100], "max_g": [180, 400], "step_g": [5, 25]},
    "dairy": {"min_g": [30, 150], "max_g": [150, 500], "step_g": [5, 25]},
    "oil_or_fat": {"min_g": [1, 5], "max_g": [15, 50], "step_g": [1, 5]},
    "condiment": {"min_g": [1, 5], "max_g": [10, 50], "step_g": [1, 5]},
    "beverage": {"min_g": [100, 250], "max_g": [300, 1000], "step_g": [10, 50]},
    "mixed_dish": {"min_g": [80, 200], "max_g": [300, 800], "step_g": [10, 50]},
}


def validate_profile_portions(profile_key: str, *, minimum, maximum, step) -> tuple[str, ...]:
    profile = PORTION_PROFILES.get(profile_key)
    if not profile:
        return (f"unknown portion profile: {profile_key}",)
    errors = []
    for value, key, label in (
        (minimum, "min_g", "minimum"),
        (maximum, "max_g", "maximum"),
        (step, "step_g", "step"),
    ):
        lower, upper = profile[key]
        if value < lower or value > upper:
            errors.append(f"{label} {value} g is outside {profile_key} orientation [{lower}, {upper}]")
    return tuple(errors)


__all__ = ["ENRICHMENT_PROFILE_VERSION", "PORTION_PROFILES", "validate_profile_portions"]
