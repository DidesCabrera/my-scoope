from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MEALS_PER_DAY = 4

MEAL_HOURS = {
    1: ("13:00",),
    2: ("13:00", "20:00"),
    3: ("10:00", "14:00", "20:00"),
    4: ("09:00", "13:00", "17:00", "21:00"),
    5: ("08:00", "11:00", "14:00", "17:00", "21:00"),
    6: ("08:00", "10:30", "13:00", "16:00", "19:00", "21:30"),
}

MEAL_LABELS = {
    1: ("Comida principal",),
    2: ("Comida 1", "Comida 2"),
    3: ("Desayuno", "Almuerzo", "Cena"),
    4: ("Desayuno", "Almuerzo", "Snack", "Cena"),
    5: ("Desayuno", "Media mañana", "Almuerzo", "Snack", "Cena"),
    6: ("Desayuno", "Media mañana", "Almuerzo", "Snack", "Cena", "Colación"),
}

MEAL_KCAL_ALLOCATION = {
    1: (1.0,),
    2: (0.48, 0.52),
    3: (0.28, 0.38, 0.34),
    4: (0.24, 0.34, 0.16, 0.26),
    5: (0.22, 0.12, 0.32, 0.14, 0.20),
    6: (0.20, 0.10, 0.30, 0.12, 0.20, 0.08),
}

SNACK_LABELS = {"snack", "colación", "colacion", "media mañana", "media manana"}
BREAKFAST_LABELS = {"desayuno"}
DINNER_LABELS = {"cena"}


@dataclass(frozen=True)
class MealRoleTemplate:
    role: str
    required: bool
    minimum_g: float
    maximum_g: float
    step_g: float = 5

    def as_dict(self) -> dict:
        return {
            "role": self.role,
            "required": self.required,
            "minimum_g": round(float(self.minimum_g), 2),
            "maximum_g": round(float(self.maximum_g), 2),
            "step_g": round(float(self.step_g), 2),
        }


@dataclass(frozen=True)
class MealTemplate:
    index: int
    label: str
    hour: str
    kind: str
    kcal_allocation: float
    roles: tuple[MealRoleTemplate, ...]

    @property
    def is_snack(self) -> bool:
        return self.kind == "snack"

    @property
    def include_vegetable(self) -> bool:
        return any(role.role == "vegetable" for role in self.roles)

    @property
    def required_roles(self) -> tuple[str, ...]:
        return tuple(role.role for role in self.roles if role.required)

    def role_template(self, role: str) -> MealRoleTemplate | None:
        for role_template in self.roles:
            if role_template.role == role:
                return role_template
        return None

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "label": self.label,
            "hour": self.hour,
            "kind": self.kind,
            "kcal_allocation": round(float(self.kcal_allocation), 4),
            "roles": [role.as_dict() for role in self.roles],
        }


def build_dailyplan_meal_templates(meals_per_day: int | None) -> tuple[MealTemplate, ...]:
    """Build deterministic meal structure for a generated DailyPlan.

    The template layer decides the shape of each meal before candidate
    selection and portion solving. This keeps the generator from treating a
    snack, lunch and dinner as the same problem with different labels.
    """

    count = normalize_meals_per_day(meals_per_day)
    labels = MEAL_LABELS.get(count, MEAL_LABELS[DEFAULT_MEALS_PER_DAY])
    hours = MEAL_HOURS.get(count, MEAL_HOURS[DEFAULT_MEALS_PER_DAY])
    allocations = normalized_meal_allocations(count)

    return tuple(
        MealTemplate(
            index=index,
            label=labels[index],
            hour=hours[index],
            kind=classify_meal_kind(labels[index], index=index, meals_per_day=count),
            kcal_allocation=allocations[index],
            roles=roles_for_meal_kind(classify_meal_kind(labels[index], index=index, meals_per_day=count)),
        )
        for index in range(count)
    )


def normalize_meals_per_day(value: int | None) -> int:
    if value is None:
        return DEFAULT_MEALS_PER_DAY
    return max(1, min(int(value), 6))


def normalized_meal_allocations(meals_per_day: int) -> tuple[float, ...]:
    raw_allocations = MEAL_KCAL_ALLOCATION.get(meals_per_day)
    if not raw_allocations:
        raw_allocations = tuple(1 / meals_per_day for _ in range(meals_per_day))

    total = sum(raw_allocations) or 1
    return tuple(value / total for value in raw_allocations)


def classify_meal_kind(label: str, *, index: int, meals_per_day: int) -> str:
    normalized_label = _normalize_label(label)

    if normalized_label in BREAKFAST_LABELS:
        return "breakfast"

    if normalized_label in SNACK_LABELS:
        return "snack"

    if normalized_label in DINNER_LABELS:
        return "dinner"

    if meals_per_day == 1:
        return "main"

    if index == meals_per_day - 1:
        return "dinner"

    return "main"


def roles_for_meal_kind(kind: str) -> tuple[MealRoleTemplate, ...]:
    if kind == "breakfast":
        return (
            MealRoleTemplate("protein", required=True, minimum_g=80, maximum_g=240),
            MealRoleTemplate("carb", required=True, minimum_g=30, maximum_g=170),
            MealRoleTemplate("fat", required=False, minimum_g=5, maximum_g=25),
        )

    if kind == "snack":
        return (
            MealRoleTemplate("protein", required=True, minimum_g=60, maximum_g=220),
            MealRoleTemplate("carb", required=True, minimum_g=20, maximum_g=130),
            MealRoleTemplate("fat", required=False, minimum_g=5, maximum_g=25),
        )

    if kind == "dinner":
        return (
            MealRoleTemplate("protein", required=True, minimum_g=90, maximum_g=260),
            MealRoleTemplate("carb", required=True, minimum_g=30, maximum_g=190),
            MealRoleTemplate("vegetable", required=False, minimum_g=50, maximum_g=200),
            MealRoleTemplate("fat", required=False, minimum_g=5, maximum_g=30),
        )

    return (
        MealRoleTemplate("protein", required=True, minimum_g=100, maximum_g=290),
        MealRoleTemplate("carb", required=True, minimum_g=45, maximum_g=250),
        MealRoleTemplate("vegetable", required=False, minimum_g=50, maximum_g=220),
        MealRoleTemplate("fat", required=False, minimum_g=5, maximum_g=35),
    )


def _normalize_label(label: str) -> str:
    value = str(label or "").strip().lower()
    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for source, target in replacements.items():
        value = value.replace(source, target)
    return " ".join(value.split())
