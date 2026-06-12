from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

from notas.presentation.resolvers.title_resolvers import CategoryBadgeUI
from notas.presentation.viewmodels.components.header_vm import HeaderVM


# =========================
# UI ATOMS
# =========================

@dataclass
class FoodsAggregationUI:
    foods_aggregation: List[Dict[str, Any]]


@dataclass
class MenuMealUI:
    meal_name: str
    foods: List[str]
    target_id: Optional[str] = None


@dataclass
class MenuUI:
    meals: List[MenuMealUI]


@dataclass
class StructuralIndicatorsUI:
    meals_count: Optional[int] = None
    foods_count: Optional[int] = None


@dataclass
class TitleUI:
    name: str
    label: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    category_badge: Optional[CategoryBadgeUI] = None
    structural_indicators: Optional[StructuralIndicatorsUI] = None


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
class IfShared:
    child_id: int
    share_id: Optional[int] = None


# =========================
# CARDS
# =========================

@dataclass
class ChildCardUI:
    child_id: float
    titulo: TitleUI
    kpis: KPIUI
    table: dict
    menu: MenuUI
    foods_aggregation: FoodsAggregationUI
    metadata: MetadataUI
    actions: list
    if_shared: Optional[IfShared] = None


# =========================
# ROOT VIEWMODEL
# =========================

@dataclass
class ListVM:
    header: HeaderVM = field(default_factory=HeaderVM)
    child_cards: List[ChildCardUI] = field(default_factory=list)
    list_mode: str = "list"

    def as_context(self):
        return {
            "ui": asdict(self)
        }