#Que necesita el picker para funcionar"
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class MealPickerContext:
    dailyplan: dict
    mode: str
    editing: dict | None

    def as_dict(self):
        return {
            "dailyplan": self.dailyplan,
            "mode": self.mode,
            "editing": self.editing,
        }

@dataclass
class MealPickerMealsPayload:
    meals: list[dict]

    def as_list(self):
        return self.meals

