from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Iterable

from notas.domain.constants.nutrition import (
    CARBS_KCAL_PER_GRAM,
    FAT_KCAL_PER_GRAM,
    PROTEIN_KCAL_PER_GRAM,
)


PROTEIN_KEYWORDS = (
    "pollo",
    "huevo",
    "huevos",
    "atun",
    "atún",
    "pescado",
    "carne",
    "vacuno",
    "pavo",
    "cerdo",
    "yogur",
    "yogurt",
    "quesillo",
    "queso cottage",
    "proteina",
    "proteína",
    "tofu",
    "tempeh",
)

CARB_KEYWORDS = (
    "arroz",
    "avena",
    "quinoa",
    "papa",
    "camote",
    "pan",
    "pasta",
    "fideos",
    "lentejas",
    "porotos",
    "garbanzos",
    "platano",
    "plátano",
    "fruta",
    "manzana",
    "berries",
    "arandanos",
    "arándanos",
)

FAT_KEYWORDS = (
    "palta",
    "nuez",
    "nueces",
    "mani",
    "maní",
    "aceite",
    "almendra",
    "almendras",
    "mantequilla de mani",
    "mantequilla de maní",
    "semilla",
    "semillas",
)

VEGETABLE_KEYWORDS = (
    "tomate",
    "lechuga",
    "zanahoria",
    "brocoli",
    "brócoli",
    "espinaca",
    "pepino",
    "zapallo italiano",
    "verdura",
    "vegetal",
    "hortaliza",
)

PROTEIN_GROUP_KEYWORDS = (
    "meat",
    "poultry",
    "fish",
    "seafood",
    "egg",
    "dairy",
    "protein",
    "proteins",
    "carnes",
    "aves",
    "pescados",
    "huevos",
    "lacteos",
    "lácteos",
)

CARB_GROUP_KEYWORDS = (
    "grain",
    "cereal",
    "starch",
    "legume",
    "fruit",
    "granos",
    "cereales",
    "tuberculos",
    "tubérculos",
    "legumbres",
    "frutas",
)

FAT_GROUP_KEYWORDS = (
    "fat",
    "oil",
    "nuts",
    "seed",
    "grasas",
    "aceites",
    "frutos secos",
    "semillas",
)

VEGETABLE_GROUP_KEYWORDS = (
    "vegetable",
    "vegetables",
    "verduras",
    "hortalizas",
)

ROLE_ORDER = ("protein", "carb", "fat", "vegetable")


class CandidateSelectionError(ValueError):
    pass


@dataclass(frozen=True)
class NutritionFoodCandidate:
    """Food information required by the nutrition engine selector.

    This dataclass deliberately does not depend on Django models, so the same
    selector can be reused later from chat flows, MCP tools or external AI
    orchestration without loading presentation code.
    """

    food_id: int
    name: str
    protein: float
    carbs: float
    fat: float
    kcal_per_100g: float
    food_group: str = ""
    food_subgroup: str = ""
    data_quality_score: int = 0
    is_verified: bool = False

    @property
    def search_text(self) -> str:
        return normalize_text(" ".join((self.name, self.food_group, self.food_subgroup)))


@dataclass(frozen=True)
class RoleCandidate:
    food: NutritionFoodCandidate
    role: str
    role_score: float
    total_score: float
    reasons: list[str] = field(default_factory=list)

    @property
    def food_id(self) -> int:
        return self.food.food_id


@dataclass(frozen=True)
class MealCandidateSelection:
    protein_id: int
    carb_id: int
    fat_id: int | None
    vegetable_id: int | None
    selected_roles: dict[str, int | None]
    diagnostics: dict

    def as_dict(self) -> dict:
        return {
            "protein_id": self.protein_id,
            "carb_id": self.carb_id,
            "fat_id": self.fat_id,
            "vegetable_id": self.vegetable_id,
            "selected_roles": dict(self.selected_roles),
            "diagnostics": self.diagnostics,
        }


def select_meal_food_candidates(
    *,
    foods: list[NutritionFoodCandidate],
    excluded_terms: Iterable[str] = (),
    preferred_terms: Iterable[str] = (),
    soft_avoid_ids: set[int] | None = None,
    is_snack: bool = False,
    include_vegetable: bool = True,
) -> MealCandidateSelection:
    """Select coherent food candidates for one generated meal.

    The selector is intentionally deterministic. It applies hard exclusions
    first, classifies foods by macro role, avoids reusing the same food in two
    roles, then scores candidates by role fit, quality and user preference.
    """

    soft_avoid_ids = soft_avoid_ids or set()
    normalized_exclusions = normalize_terms(excluded_terms)
    normalized_preferences = normalize_terms(preferred_terms)
    usable_foods = [
        food
        for food in foods
        if food.kcal_per_100g > 0
        and not matches_any(food.search_text, normalized_exclusions)
    ]

    if not usable_foods:
        raise CandidateSelectionError("candidate_selector_requires_usable_foods")

    selected: dict[str, RoleCandidate | None] = {}
    used_ids: set[int] = set()
    diagnostics: dict[str, dict] = {
        "excluded_terms": list(normalized_exclusions),
        "preferred_terms": list(normalized_preferences),
        "candidate_counts": {},
        "selected": {},
    }

    for role in ROLE_ORDER:
        if role == "vegetable" and (is_snack or not include_vegetable):
            selected[role] = None
            continue

        role_candidates = build_role_candidates(
            foods=usable_foods,
            role=role,
            preferred_terms=normalized_preferences,
            soft_avoid_ids=soft_avoid_ids,
        )
        diagnostics["candidate_counts"][role] = len(role_candidates)
        role_candidates = [
            candidate
            for candidate in role_candidates
            if candidate.food_id not in used_ids
        ]

        if not role_candidates:
            if role in {"protein", "carb"}:
                raise CandidateSelectionError(f"candidate_selector_missing_required_{role}")
            selected[role] = None
            continue

        choice = role_candidates[0]
        selected[role] = choice
        used_ids.add(choice.food_id)
        diagnostics["selected"][role] = {
            "food_id": choice.food_id,
            "name": choice.food.name,
            "role_score": round(choice.role_score, 4),
            "total_score": round(choice.total_score, 4),
            "reasons": list(choice.reasons),
        }

    protein = selected.get("protein")
    carb = selected.get("carb")

    if protein is None or carb is None:
        raise CandidateSelectionError("candidate_selector_missing_required_roles")

    fat = selected.get("fat")
    vegetable = selected.get("vegetable")

    return MealCandidateSelection(
        protein_id=protein.food_id,
        carb_id=carb.food_id,
        fat_id=fat.food_id if fat else None,
        vegetable_id=vegetable.food_id if vegetable else None,
        selected_roles={
            "protein": protein.food_id,
            "carb": carb.food_id,
            "fat": fat.food_id if fat else None,
            "vegetable": vegetable.food_id if vegetable else None,
        },
        diagnostics=diagnostics,
    )


def build_role_candidates(
    *,
    foods: list[NutritionFoodCandidate],
    role: str,
    preferred_terms: Iterable[str] = (),
    soft_avoid_ids: set[int] | None = None,
) -> list[RoleCandidate]:
    soft_avoid_ids = soft_avoid_ids or set()
    normalized_preferences = normalize_terms(preferred_terms)
    candidates = []

    for food in foods:
        role_score, reasons = classify_food_for_role(food=food, role=role)
        if role_score <= 0:
            continue

        total_score = role_score * 1000

        if matches_any(food.search_text, normalized_preferences):
            total_score += 220
            reasons.append("preferred")

        if food.food_id in soft_avoid_ids:
            total_score -= 80
            reasons.append("soft_avoid_penalty")

        if food.is_verified:
            total_score += 35
            reasons.append("verified")

        total_score += min(max(int(food.data_quality_score or 0), 0), 100) / 4
        candidates.append(
            RoleCandidate(
                food=food,
                role=role,
                role_score=role_score,
                total_score=total_score,
                reasons=reasons,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.total_score,
            candidate.role_score,
            candidate.food.is_verified,
            candidate.food.data_quality_score,
            -candidate.food_id,
        ),
        reverse=True,
    )
    return candidates


def classify_food_for_role(*, food: NutritionFoodCandidate, role: str) -> tuple[float, list[str]]:
    ratios = macro_energy_ratios(food)
    search_text = food.search_text
    reasons: list[str] = []

    if role == "protein":
        keyword_score = 0.95 if matches_any(search_text, PROTEIN_KEYWORDS + PROTEIN_GROUP_KEYWORDS) else 0.0
        macro_score = ratios["protein"] if food.protein >= 8 else 0.0
        if keyword_score:
            reasons.append("protein_keyword")
        if macro_score:
            reasons.append("protein_density")
        return max(keyword_score, macro_score), reasons

    if role == "carb":
        keyword_score = 0.95 if matches_any(search_text, CARB_KEYWORDS + CARB_GROUP_KEYWORDS) else 0.0
        macro_score = ratios["carbs"] if food.carbs >= 10 else 0.0
        # Prevent oils/nuts from becoming carbs only because of a broad group.
        if ratios["fat"] > 0.55 and not keyword_score:
            macro_score = 0.0
        if keyword_score:
            reasons.append("carb_keyword")
        if macro_score:
            reasons.append("carb_density")
        return max(keyword_score, macro_score), reasons

    if role == "fat":
        keyword_score = 0.95 if matches_any(search_text, FAT_KEYWORDS + FAT_GROUP_KEYWORDS) else 0.0
        macro_score = ratios["fat"] if food.fat >= 5 else 0.0
        if keyword_score:
            reasons.append("fat_keyword")
        if macro_score:
            reasons.append("fat_density")
        return max(keyword_score, macro_score), reasons

    if role == "vegetable":
        keyword_score = 0.95 if matches_any(search_text, VEGETABLE_KEYWORDS + VEGETABLE_GROUP_KEYWORDS) else 0.0
        macro_score = 0.0
        if food.kcal_per_100g <= 85 and food.fat <= 3 and food.protein <= 7:
            macro_score = 0.55
        if keyword_score:
            reasons.append("vegetable_keyword")
        if macro_score:
            reasons.append("low_energy_vegetable_like")
        return max(keyword_score, macro_score), reasons

    return 0.0, reasons


def macro_energy_ratios(food: NutritionFoodCandidate) -> dict[str, float]:
    kcal = max(float(food.kcal_per_100g or 0), 1.0)
    return {
        "protein": max(0.0, float(food.protein)) * PROTEIN_KCAL_PER_GRAM / kcal,
        "carbs": max(0.0, float(food.carbs)) * CARBS_KCAL_PER_GRAM / kcal,
        "fat": max(0.0, float(food.fat)) * FAT_KCAL_PER_GRAM / kcal,
    }


def normalize_terms(values: Iterable[str]) -> list[str]:
    return [
        normalized
        for value in values
        if (normalized := normalize_text(value))
    ]


def normalize_text(value: str) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    return "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )


def matches_any(text: str, terms: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return any(term and normalize_text(term) in normalized for term in terms)
