from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from notas.presentation.resolvers.title_resolvers import CategoryBadgeUI

# =========================
# UI ATOMS
# =========================
@dataclass
class FoodsAggregationUI:
    foods_aggregation: List[Dict[str, Any]]

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

@dataclass
class MetadataUI:
    owner: str
    author: str
    fork_from: Optional[str]
    

# === Related_data ESPECIFICOS ===

@dataclass
class DpmRelatedDataUI:
    rel_id: float
    hour: Optional[str]
    note: Optional[str]
    alloc_protein: float
    alloc_carbs: float
    alloc_fat: float


# =========================
# CARDS
# =========================

@dataclass
class MainCardUI:
    main_id: float
    titulo: TitleUI
    kpis: KPIUI
    table: dict
    metadata: MetadataUI
    menu: Optional[dict] = None
    # Presentation flags
    show_kpis: bool = False
    show_table: bool = False


@dataclass
class ChildCardUI:
    main_id:float
    child_id:float
    related_data: DpmRelatedDataUI
    titulo: TitleUI
    kpis: KPIUI
    table: dict
    foods_aggregation: FoodsAggregationUI
    metadata: MetadataUI
    actions: list


# =========================
# ROOT VIEWMODEL
# =========================

@dataclass
class DailyPlanDetailVM:

    header: dict
    main_card: MainCardUI
    structural_indicators: Optional[StructuralIndicatorsUI]
    foods_aggregation: FoodsAggregationUI
    foods_aggregation_table: list
    child_cards: List[ChildCardUI]

    def as_context(self):
        return {
            "ui": asdict(self)
        }
