from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class MealKpiDTO:
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
class MealFoodDTO:
    mealfood_id: int
    food_id: int
    food_name: str
    quantity: float
    protein: float
    carbs: float
    fat: float
    total_kcal: float
    kcal_protein: float
    kcal_carbs: float
    kcal_fat: float
    alloc_protein: float
    alloc_carbs: float
    alloc_fat: float
    quantity_unit: str = "g"
    ppk: float | None = None
    emoji: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MealListItemDTO:
    id: int
    name: str
    category: str
    created_by_id: int | None
    original_author_id: int | None
    foods_count: int
    is_public: bool
    is_forkable: bool
    is_copiable: bool
    is_draft: bool
    kpis: MealKpiDTO

    def as_dict(self) -> dict:
        data = asdict(self)
        data["kpis"] = self.kpis.as_dict()
        return data


@dataclass(frozen=True)
class MealDTO:
    id: int
    name: str
    category: str
    created_by_id: int | None
    original_author_id: int | None
    foods_count: int
    is_public: bool
    is_forkable: bool
    is_copiable: bool
    is_draft: bool
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