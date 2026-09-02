from dataclasses import asdict, dataclass
from typing import List, Optional

from notas.presentation.resolvers.title_resolvers import CategoryBadgeUI
from notas.presentation.viewmodels.components.entity_heading_vm import EntitySubtitleVM

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
    subtitle: Optional[EntitySubtitleVM] = None


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
class FatherCardUI:
    father_id: float
    titulo: TitleUI
    rel_id: float
    kpis: KPIUI
    related_data: DpmRelatedDataUI

@dataclass
class MainCardUI:
    main_id: float
    titulo: TitleUI
    kpis: KPIUI
    table: dict
    metadata: MetadataUI
    foods_aggregation: Optional[list] = None


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
class DpmDeepDetailVM:

    header: dict
    father_card: FatherCardUI
    main_card: MainCardUI
    child_cards: List[ChildCardUI]

    def as_context(self):
        return {
            "ui": asdict(self)
        }
