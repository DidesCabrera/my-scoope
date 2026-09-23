"""Versioned, framework-independent requirements shared by manual and AI planning.

Projected weights are assumptions, never measurements. Unknown fields fail closed.
"""

from dataclasses import asdict, dataclass, field
from math import isfinite


def number(value, key, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"program_spec_{key}_number_required")
    value = float(value)
    if not isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"program_spec_{key}_out_of_range")
    return value


@dataclass(frozen=True)
class WeekTarget:
    week: int
    kcal: float
    reference_weight_kg: float
    projected_weight_kg: float | None
    protein_min_g: float
    protein_max_g: float


@dataclass(frozen=True)
class ProgramSpecification:
    version: int
    duration_weeks: int
    meals_per_day: int
    weight_basis: str
    measured_weight_kg: float
    protein_min_ppk: float
    protein_max_ppk: float
    fat_max_percent: float
    calorie_tolerance_percent: float
    fruit_min_g: float
    vegetable_min_g: float
    weekly_fruit_species: int
    weekly_vegetable_species: int
    max_family_per_week_per_slot: int
    weeks: tuple[WeekTarget, ...]
    energy_source: str = "manual"
    macro_distribution: dict = field(default_factory=dict)
    macro_tolerance_percent: float = 5.0

    def as_dict(self):
        result = asdict(self)
        result["weeks"] = [asdict(week) for week in self.weeks]
        return result


INPUT_FIELDS = {
    "version", "duration_weeks", "meals_per_day", "weight_basis", "measured_weight_kg",
    "protein_min_ppk", "protein_max_ppk", "fat_max_percent", "calorie_tolerance_percent",
    "fruit_min_g", "vegetable_min_g", "weekly_fruit_species", "weekly_vegetable_species",
    "max_family_per_week_per_slot", "weeks", "energy_source",
    "macro_distribution", "macro_tolerance_percent",
}


def parse_program_specification(value):
    if not isinstance(value, dict) or set(value) - INPUT_FIELDS:
        raise ValueError("program_spec_unknown_or_invalid_fields")
    if value.get("version") != 1 or type(value.get("version")) is not int:
        raise ValueError("program_spec_version_unsupported")
    ints = {}
    for key, low, high in (
        ("duration_weeks", 1, 8), ("meals_per_day", 1, 6),
        ("weekly_fruit_species", 0, 7), ("weekly_vegetable_species", 0, 14),
        ("max_family_per_week_per_slot", 1, 7),
    ):
        raw = value.get(key)
        if type(raw) is not int or not low <= raw <= high:
            raise ValueError(f"program_spec_{key}_out_of_range")
        ints[key] = raw
    floats = {}
    for key, low, high in (
        ("measured_weight_kg", 20, 400), ("protein_min_ppk", 0.1, 3.5),
        ("protein_max_ppk", 0.1, 3.5), ("fat_max_percent", 1, 100),
        ("calorie_tolerance_percent", 0, 10), ("fruit_min_g", 0, 2000),
        ("vegetable_min_g", 0, 3000),
    ):
        floats[key] = number(value.get(key), key, low, high)
    if floats["protein_min_ppk"] > floats["protein_max_ppk"]:
        raise ValueError("program_spec_protein_interval_reversed")
    basis = value.get("weight_basis")
    if basis not in {"measured", "projected"}:
        raise ValueError("program_spec_weight_basis_required")
    source = value.get("energy_source", "manual")
    if source not in {"manual", "estimated"}:
        raise ValueError("program_spec_energy_source_invalid")
    distribution = value.get("macro_distribution") or {}
    if distribution:
        if not isinstance(distribution, dict) or set(distribution) != {"protein", "carbs", "fat"}:
            raise ValueError("program_spec_macro_distribution_invalid")
        distribution = {key: number(item, key, .01, 99.99) for key, item in distribution.items()}
        if abs(sum(distribution.values()) - 100) > .01:
            raise ValueError("program_spec_macro_distribution_sum_invalid")
    macro_tolerance = number(value.get("macro_tolerance_percent", 5), "macro_tolerance_percent", 0, 20)
    if distribution and distribution["fat"] * (1 - macro_tolerance / 100) > floats["fat_max_percent"]:
        raise ValueError("program_spec_macro_distribution_conflicts_fat_cap")
    rows = value.get("weeks")
    if not isinstance(rows, list) or len(rows) != ints["duration_weeks"]:
        raise ValueError("program_spec_complete_week_targets_required")
    weeks = _parse_week_targets(rows, basis, floats)
    return ProgramSpecification(version=1, weight_basis=basis, weeks=tuple(weeks),
                                energy_source=source, macro_distribution=distribution,
                                macro_tolerance_percent=macro_tolerance, **ints, **floats)


def _parse_week_targets(rows, basis, floats):
    weeks = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or set(row) - {
            "week", "kcal", "projected_weight_kg", "reference_weight_kg", "protein_min_g", "protein_max_g",
        } or type(row.get("week")) is not int or row["week"] != index:
            raise ValueError("program_spec_week_order_invalid")
        kcal = number(row.get("kcal"), "kcal", 800, 8000)
        projection = row.get("projected_weight_kg")
        if projection is not None:
            projection = number(projection, "projected_weight_kg", 20, 400)
        if basis == "projected" and projection is None:
            raise ValueError("program_spec_projected_weight_required")
        weight = projection if basis == "projected" else floats["measured_weight_kg"]
        week = WeekTarget(index, kcal, weight, projection,
                          weight * floats["protein_min_ppk"], weight * floats["protein_max_ppk"])
        # Derived fields may be present in persisted snapshots, but never contradict inputs.
        for key in ("reference_weight_kg", "protein_min_g", "protein_max_g"):
            if key in row and abs(number(row[key], key, 0, 10000) - getattr(week, key)) > 1e-6:
                raise ValueError("program_spec_derived_target_mismatch")
        if week.protein_min_g * 4 > kcal * (1 + floats["calorie_tolerance_percent"] / 100):
            raise ValueError("program_spec_protein_exceeds_energy")
        weeks.append(week)
    return weeks


def linear_week_targets(*, duration_weeks, start_kcal, end_kcal, start_weight, end_weight):
    """Preview only: callers must explicitly choose/confirm a projected trajectory."""
    if type(duration_weeks) is not int or not 1 <= duration_weeks <= 8:
        raise ValueError("program_spec_duration_weeks_out_of_range")
    for value, key, low, high in ((start_kcal, "kcal", 800, 8000), (end_kcal, "kcal", 800, 8000),
                                (start_weight, "weight", 20, 400), (end_weight, "weight", 20, 400)):
        number(value, key, low, high)
    if duration_weeks == 1 and (start_kcal != end_kcal or start_weight != end_weight):
        raise ValueError("program_spec_single_week_endpoints_differ")
    return [{"week": index + 1,
             "kcal": round(start_kcal + (end_kcal - start_kcal) * index / max(duration_weeks - 1, 1), 2),
             "projected_weight_kg": round(start_weight + (end_weight - start_weight) * index / max(duration_weeks - 1, 1), 3)}
            for index in range(duration_weeks)]
