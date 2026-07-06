from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MacroTarget:
    """Macro target used by the nutrition engine.

    Values are daily or per-meal depending on the caller context.
    """

    kcal: float
    protein: float
    carbs: float
    fat: float

    def as_dict(self) -> dict:
        return {
            "kcal": round(float(self.kcal), 2),
            "protein": round(float(self.protein), 2),
            "carbs": round(float(self.carbs), 2),
            "fat": round(float(self.fat), 2),
        }


@dataclass(frozen=True)
class PortionBounds:
    minimum_g: float
    maximum_g: float
    step_g: float = 5

    def normalized(self) -> "PortionBounds":
        minimum = max(0.0, float(self.minimum_g))
        maximum = max(minimum, float(self.maximum_g))
        step = max(1.0, float(self.step_g or 5))
        return PortionBounds(
            minimum_g=minimum,
            maximum_g=maximum,
            step_g=step,
        )


@dataclass(frozen=True)
class SolverFood:
    food_id: int
    name: str
    role: str
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    kcal_per_100g: float
    bounds: PortionBounds
    required: bool = True

    def macros_for_quantity(self, quantity_g: float) -> MacroTarget:
        factor = float(quantity_g) / 100.0
        return MacroTarget(
            kcal=self.kcal_per_100g * factor,
            protein=self.protein_per_100g * factor,
            carbs=self.carbs_per_100g * factor,
            fat=self.fat_per_100g * factor,
        )


@dataclass(frozen=True)
class SolvedFoodPortion:
    food_id: int
    name: str
    role: str
    quantity_g: float
    macros: MacroTarget

    def as_dict(self) -> dict:
        return {
            "food_id": self.food_id,
            "name": self.name,
            "role": self.role,
            "quantity_g": round(float(self.quantity_g), 2),
            "macros": self.macros.as_dict(),
        }


@dataclass(frozen=True)
class PortionSolverDiagnostics:
    score: float
    iterations: int
    target: MacroTarget
    actual: MacroTarget
    diff: MacroTarget
    diff_percent: dict[str, float | None]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "score": round(float(self.score), 4),
            "iterations": int(self.iterations),
            "target": self.target.as_dict(),
            "actual": self.actual.as_dict(),
            "diff": self.diff.as_dict(),
            "diff_percent": {
                key: round(value, 2) if value is not None else None
                for key, value in self.diff_percent.items()
            },
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class PortionSolverResult:
    portions: list[SolvedFoodPortion]
    diagnostics: PortionSolverDiagnostics

    def as_dict(self) -> dict:
        return {
            "portions": [portion.as_dict() for portion in self.portions],
            "diagnostics": self.diagnostics.as_dict(),
        }
