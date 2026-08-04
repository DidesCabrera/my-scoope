from dataclasses import asdict, dataclass
from typing import List, Optional

from notas.presentation.resolvers.title_resolvers import CategoryBadgeUI

# =========================
# UI ATOMS
# =========================

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
class MfRelatedDataUI:
    rel_id: float
    quantity: float
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
    foods_aggregation: Optional[list] = None
    # Presentation flags
    show_kpis: bool = False
    show_table: bool = False


@dataclass
class ChildCardUI:
    child_id:float
    related_data: MfRelatedDataUI
    titulo: TitleUI
    kpis: KPIUI
    actions: list


# =========================
# ROOT VIEWMODEL
# =========================

@dataclass
class MealDetailVM:

    header: dict
    main_card: MainCardUI
    child_cards: List[ChildCardUI]

    def as_context(self):
        return {
            "ui": asdict(self)
        }
