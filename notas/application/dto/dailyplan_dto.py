from dataclasses import asdict, dataclass

from notas.application.dto.meal_dto import MealFoodDTO, MealKpiDTO


@dataclass(frozen=True)
class DailyPlanKpiDTO:
    ppk: float
    total_kcal: float
    protein: float
    carbs: float
    fat: float
    kcal_protein: float
    kcal_carbs: float
    kcal_fat: float
    alloc_protein: float
    alloc_carbs: float
    alloc_fat: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DailyPlanMealDTO:
    dailyplanmeal_id: int
    meal_id: int
    meal_name: str
    hour: str | None
    note: str | None
    order: int
    foods_count: int
    kpis: MealKpiDTO
    foods: list[MealFoodDTO]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["kpis"] = self.kpis.as_dict()
        data["foods"] = [
            food.as_dict()
            for food in self.foods
        ]
        return data


@dataclass(frozen=True)
class DailyPlanFoodAggregationDTO:
    food_id: int
    food_name: str
    quantity: float
    quantity_unit: str
    protein: float
    carbs: float
    fat: float
    total_kcal: float
    image_path: str | None = None

    def as_dict(self) -> dict:
        data = asdict(self)
        if data["image_path"] is None:
            del data["image_path"]
        return data


@dataclass(frozen=True)
class DailyPlanListItemDTO:
    id: int
    name: str
    category: str
    created_by_id: int | None
    original_author_id: int | None
    meals_count: int
    foods_count: int
    is_public: bool
    is_forkable: bool
    is_copiable: bool
    is_draft: bool
    kpis: DailyPlanKpiDTO

    def as_dict(self) -> dict:
        data = asdict(self)
        data["kpis"] = self.kpis.as_dict()
        return data


@dataclass(frozen=True)
class DailyPlanDTO:
    id: int
    name: str
    category: str
    created_by_id: int | None
    original_author_id: int | None
    meals_count: int
    foods_count: int
    is_public: bool
    is_forkable: bool
    is_copiable: bool
    is_draft: bool
    kpis: DailyPlanKpiDTO
    meals: list[DailyPlanMealDTO]
    foods_aggregation: list[DailyPlanFoodAggregationDTO]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["kpis"] = self.kpis.as_dict()
        data["meals"] = [
            meal.as_dict()
            for meal in self.meals
        ]
        data["foods_aggregation"] = [
            food.as_dict()
            for food in self.foods_aggregation
        ]
        return data
