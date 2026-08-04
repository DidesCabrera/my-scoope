#Que necesita el picker para funcionar"
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FoodPickerLegacyContext:
    meal: dict
    mode: str
    editing: dict | None

    def as_dict(self):
        return {
            "meal": self.meal,
            "mode": self.mode,
            "editing": self.editing,
        }

@dataclass
class FoodPickerFoodsPayload:
    foods: list[dict]

    def as_list(self):
        return self.foods

