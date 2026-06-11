from dataclasses import dataclass, asdict, field
from typing import List, Optional

from notas.presentation.resolvers.title_resolvers import CategoryBadgeUI
from notas.presentation.viewmodels.components.header_vm import HeaderVM


@dataclass
class StructuralIndicatorsUI:
    meals_count: Optional[int] = None
    foods_count: Optional[int] = None


@dataclass
class FoodBadgeUI:
    label: str
    modifier: str = "default"


@dataclass
class TitleUI:
    name: str
    label: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    category_badge: Optional[CategoryBadgeUI] = None
    structural_indicators: Optional[StructuralIndicatorsUI] = None
    badges: List[FoodBadgeUI] = field(default_factory=list)


@dataclass
class KPIUI:
    ppk: float
    tot_kcal: float
    g_protein: float
    g_carbs: float
    g_fat: float
    kcal_protein: float
    kcal_carbs: float
    kcal_fat: float
    alloc_protein: float
    alloc_carbs: float
    alloc_fat: float
    pct_outside_protein: bool = False
    pct_outside_carbs: bool = False
    pct_outside_fat: bool = False


@dataclass
class MetadataUI:
    owner: str
    author: str
    fork_from: Optional[str]


@dataclass
class ChildCardUI:
    child_id: float
    titulo: TitleUI
    kpis: KPIUI
    metadata: MetadataUI
    actions: list


@dataclass
class FoodListVM:
    header: HeaderVM = field(default_factory=HeaderVM)
    child_cards: List[ChildCardUI] = field(default_factory=list)
    list_mode: str = "list"

    def as_context(self):
        return {
            "ui": asdict(self)
        }
