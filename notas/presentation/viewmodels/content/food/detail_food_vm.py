from dataclasses import dataclass, asdict, field
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
class FoodBadgeUI:
    label: str
    modifier: str


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
    body_weight: float
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


# =========================
# CARDS
# =========================

@dataclass
class MainCardUI:
    main_id: float
    titulo: TitleUI
    kpis: KPIUI

    # Presentation flags
    show_kpis: bool = False
    show_table: bool = False


# =========================
# ROOT VIEWMODEL
# =========================

@dataclass
class FoodDetailVM:

    header: dict
    main_card: MainCardUI

    def as_context(self):
        return {
            "ui": asdict(self)
        }
