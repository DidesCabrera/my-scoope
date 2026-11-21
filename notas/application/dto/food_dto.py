from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FoodMacroDTO:
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

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FoodListItemDTO:
    id: int
    name: str
    category: str
    created_by_id: int | None
    macros: FoodMacroDTO

    def as_dict(self) -> dict:
        data = asdict(self)
        data["macros"] = self.macros.as_dict()
        return data


@dataclass(frozen=True)
class FoodDTO:
    id: int
    name: str
    category: str
    created_by_id: int | None
    macros: FoodMacroDTO
    portion_unit: str = "g"
    image_path: str | None = None

    def as_dict(self) -> dict:
        data = asdict(self)
        data["macros"] = self.macros.as_dict()
        if data["image_path"] is None:
            del data["image_path"]
        return data
