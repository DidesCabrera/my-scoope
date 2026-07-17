from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from django.db.models import Q, QuerySet

from nutrition_solver.domain.capabilities import SolverFeatureKey
from nutrition_solver.domain.food_profiles import (
    SolverFeatureValue,
    SolverFoodProfile,
    derive_macro_role_features,
)
from nutrition_solver.domain.models import PortionBounds, SolverFood

from notas.application.queries.read_boundaries import get_readable_food_queryset
from notas.domain.models import Food


DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT = 120
MAX_SOLVER_FOOD_CANDIDATE_LIMIT = 250

_SOLVER_VISIBLE_STATES = (
    Food.VISIBILITY_CORE,
    Food.VISIBILITY_EXTENDED,
)

_ROLE_DEFAULT_BOUNDS: dict[str, tuple[float, float, float]] = {
    "protein": (80.0, 260.0, 5.0),
    "carb": (60.0, 320.0, 5.0),
    "fat": (5.0, 80.0, 5.0),
    "vegetable": (50.0, 300.0, 5.0),
    "balanced": (20.0, 250.0, 5.0),
}


@dataclass(frozen=True)
class SolverFoodCandidateQueryResult:
    """Read-model result for operational foods that are ready for the solver.

    This object intentionally exposes pure ``nutrition_solver`` candidates,
    not ``Food`` rows. It keeps catalog trace fields and provider payloads out
    of solver consumers.
    """

    candidates: tuple[SolverFood, ...]
    count: int
    limit: int
    search: str | None
    include_extended: bool

    def as_dict(self) -> dict:
        return {
            "candidates": [_solver_food_as_dict(candidate) for candidate in self.candidates],
            "count": self.count,
            "limit": self.limit,
            "search": self.search,
            "include_extended": self.include_extended,
        }


def list_solver_food_candidates(
    user,
    *,
    search: str | None = None,
    limit: int = DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT,
    include_extended: bool = True,
) -> SolverFoodCandidateQueryResult:
    """Return solver-ready operational foods for a user.

    Source boundary:
    - reads ``notas.Food`` through the existing read boundary;
    - requires ``solver_enabled=True`` and active/visible foods;
    - returns pure ``nutrition_solver.domain.models.SolverFood`` objects;
    - never exposes Food Catalog IDs, external provider references or payloads.
    """

    safe_limit = _normalize_limit(limit)
    normalized_search = _normalize_search(search)

    queryset = get_solver_food_candidate_queryset(
        user,
        search=normalized_search,
        include_extended=include_extended,
    )

    candidates = tuple(
        build_solver_food_candidate(food)
        for food in queryset[:safe_limit]
    )

    return SolverFoodCandidateQueryResult(
        candidates=candidates,
        count=len(candidates),
        limit=safe_limit,
        search=normalized_search,
        include_extended=include_extended,
    )


def get_solver_food_candidate_queryset(
    user,
    *,
    search: str | None = None,
    include_extended: bool = True,
) -> QuerySet:
    """Return the ORM queryset used only at the ``notas`` adapter boundary."""

    visibility_states = [Food.VISIBILITY_CORE]
    if include_extended:
        visibility_states.append(Food.VISIBILITY_EXTENDED)

    queryset = (
        get_readable_food_queryset(user)
        .filter(
            is_active=True,
            solver_enabled=True,
            visibility__in=visibility_states,
        )
        .order_by("-is_verified", "-data_quality_score", "name", "id")
        .distinct()
    )

    if search:
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(canonical_name__icontains=search)
            | Q(aliases__name__icontains=search)
            | Q(aliases__normalized_name__icontains=search)
        ).distinct()

    return queryset


def build_solver_food_candidate(
    food: Food,
    *,
    role: str | None = None,
    required: bool = True,
) -> SolverFood:
    """Convert one operational ``notas.Food`` row into a pure solver candidate."""

    inferred_role = _normalize_role(role) or _infer_solver_role(food)

    return SolverFood(
        food_id=int(food.id),
        name=str(food.name),
        role=inferred_role,
        protein_per_100g=float(food.protein),
        carbs_per_100g=float(food.carbs),
        fat_per_100g=float(food.fat),
        kcal_per_100g=float(food.total_kcal),
        bounds=_build_portion_bounds(food=food, role=inferred_role),
        required=bool(required),
    )


def build_solver_food_profile(
    food: Food,
    *,
    role: str | None = None,
    required: bool = True,
) -> SolverFoodProfile:
    """Build a pure profile from the stable operational snapshot only."""

    candidate = build_solver_food_candidate(food, role=role, required=required)
    payload = dict(food.solver_capabilities or {})
    values = dict(payload.get("values") or {})
    confidence = dict(payload.get("confidence") or {})
    source = str(payload.get("source") or "operational_food")
    version = str(payload.get("schema_version") or food.solver_capabilities_version)
    quality_confidence = max(0.0, min(float(food.data_quality_score or 0), 100.0))

    features = [
        SolverFeatureValue(SolverFeatureKey.NUTRIENTS, True, quality_confidence, source, version),
        SolverFeatureValue(
            SolverFeatureKey.PORTION_BOUNDS,
            {
                "minimum_g": candidate.bounds.minimum_g,
                "maximum_g": candidate.bounds.maximum_g,
                "step_g": candidate.bounds.step_g,
            },
            _feature_confidence(confidence, "portion_bounds", quality_confidence),
            source,
            version,
        ),
    ]

    if food.preparation_state != Food.PREPARATION_UNKNOWN:
        features.append(
            SolverFeatureValue(
                SolverFeatureKey.PREPARATION_STATE,
                food.preparation_state,
                _feature_confidence(confidence, "preparation_state", quality_confidence),
                source,
                version,
            )
        )

    feature_map = {
        "food_form": SolverFeatureKey.FOOD_FORM,
        "functional_roles": SolverFeatureKey.FUNCTIONAL_ROLES,
        "meal_affinities": SolverFeatureKey.MEAL_AFFINITIES,
        "dietary_tags": SolverFeatureKey.DIETARY_TAGS,
        "allergens": SolverFeatureKey.ALLERGENS,
        "preparation_effort": SolverFeatureKey.PREPARATION_EFFORT,
        "cost_band": SolverFeatureKey.COST_BAND,
    }
    for value_key, feature_key in feature_map.items():
        value = values.get(value_key)
        if value in (None, "", [], ()) or value == "unknown":
            continue
        features.append(
            SolverFeatureValue(
                feature_key,
                value,
                _feature_confidence(confidence, value_key, quality_confidence),
                source,
                version,
            )
        )

    if not any(feature.feature == SolverFeatureKey.FUNCTIONAL_ROLES for feature in features):
        features.append(derive_macro_role_features(candidate))

    return SolverFoodProfile(
        food=candidate,
        features=tuple(features),
        schema_version=version,
        metadata={"operational_food_id": food.id},
    )


def _feature_confidence(values: dict, key: str, default: float) -> float:
    try:
        return max(0.0, min(float(values.get(key, default)), 100.0))
    except (TypeError, ValueError):
        return default


def _build_portion_bounds(*, food: Food, role: str) -> PortionBounds:
    default_minimum, default_maximum, default_step = _ROLE_DEFAULT_BOUNDS.get(
        role,
        _ROLE_DEFAULT_BOUNDS["balanced"],
    )

    minimum = _clean_optional_float(food.min_portion_g)
    maximum = _clean_optional_float(food.max_portion_g)
    step = _clean_optional_float(food.portion_step_g)

    resolved_minimum = minimum if minimum is not None else default_minimum
    resolved_maximum = maximum if maximum is not None else default_maximum
    resolved_step = step if step is not None else default_step

    if resolved_maximum < resolved_minimum:
        resolved_maximum = resolved_minimum

    return PortionBounds(
        minimum_g=resolved_minimum,
        maximum_g=resolved_maximum,
        step_g=resolved_step,
    ).normalized()


def _infer_solver_role(food: Food) -> str:
    search_text = " ".join(
        part.lower()
        for part in (
            food.food_group or "",
            food.food_subgroup or "",
            food.canonical_name or "",
            food.name or "",
        )
    )

    if any(term in search_text for term in ("verdura", "vegetable", "hortaliza", "ensalada")):
        return "vegetable"
    if any(term in search_text for term in ("aceite", "oil", "grasa", "fat", "nuez", "almendra")):
        return "fat"
    if any(term in search_text for term in ("carne", "pollo", "pescado", "huevo", "protein", "proteina")):
        return "protein"
    if any(term in search_text for term in ("arroz", "pasta", "avena", "pan", "carb", "cereal")):
        return "carb"

    protein = float(food.protein)
    carbs = float(food.carbs)
    fat = float(food.fat)
    kcal = float(food.total_kcal)

    if kcal <= 80 and fat <= 3 and protein <= 6:
        return "vegetable"
    if fat >= protein and fat >= carbs and fat >= 8:
        return "fat"
    if protein >= carbs and protein >= fat:
        return "protein"
    if carbs >= protein and carbs >= fat:
        return "carb"
    return "balanced"


def _normalize_role(role: str | None) -> str | None:
    if role is None:
        return None

    normalized = str(role).strip().lower()
    return normalized or None


def _solver_food_as_dict(candidate: SolverFood) -> dict:
    bounds = candidate.bounds.normalized()
    return {
        "food_id": candidate.food_id,
        "name": candidate.name,
        "role": candidate.role,
        "protein_per_100g": round(float(candidate.protein_per_100g), 2),
        "carbs_per_100g": round(float(candidate.carbs_per_100g), 2),
        "fat_per_100g": round(float(candidate.fat_per_100g), 2),
        "kcal_per_100g": round(float(candidate.kcal_per_100g), 2),
        "bounds": {
            "minimum_g": round(float(bounds.minimum_g), 2),
            "maximum_g": round(float(bounds.maximum_g), 2),
            "step_g": round(float(bounds.step_g), 2),
        },
        "required": bool(candidate.required),
    }


def _clean_optional_float(value) -> float | None:
    if value is None:
        return None

    if isinstance(value, Decimal):
        value = float(value)

    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
        return None

    return normalized


def _normalize_search(search: str | None) -> str | None:
    if search is None or not isinstance(search, str):
        return None

    normalized = search.strip()
    return normalized or None


def _normalize_limit(limit: int) -> int:
    if isinstance(limit, bool) or not isinstance(limit, int):
        return DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT

    if limit <= 0:
        return DEFAULT_SOLVER_FOOD_CANDIDATE_LIMIT

    return min(limit, MAX_SOLVER_FOOD_CANDIDATE_LIMIT)
