from __future__ import annotations



from ai_assistant.models import AIUsageEvent
from food_catalog.models import CatalogCurationCandidate, CatalogFood

CATALOG_CANDIDATE_ACTION_STATUSES = [
    CatalogCurationCandidate.STATUS_QUEUED,
    CatalogCurationCandidate.STATUS_IN_REVIEW,
    CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
    CatalogCurationCandidate.STATUS_APPROVED_FOR_CURATION,
]

CATALOG_FOOD_REVIEW_STATUSES = [
    CatalogFood.STATUS_EXTERNAL_CANDIDATE,
    CatalogFood.STATUS_MANUAL_CANDIDATE,
    CatalogFood.STATUS_BRAND_SUBMITTED,
    CatalogFood.STATUS_NORMALIZED,
    CatalogFood.STATUS_PENDING_REVIEW,
    CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
    CatalogFood.STATUS_REVIEWED,
    CatalogFood.STATUS_VERIFIED,
    CatalogFood.STATUS_PUBLISHED,
]

CATALOG_GROUP_FAMILIES = (
    ("vegetables", "Verduras", {"vegetable", "vegetables", "verdura", "verduras", "hortalizas"}),
    ("protein", "Proteínas", {"protein", "proteins", "proteina", "proteinas", "proteína", "proteínas", "meat", "meats", "carne", "carnes", "fish", "pescado", "pescados", "poultry", "aves"}),
    ("fruit", "Frutas", {"fruit", "fruits", "fruta", "frutas"}),
    ("cereals", "Cereales", {"cereal", "cereals", "grain", "grains", "cereal", "cereales"}),
    ("legumes", "Legumbres", {"legume", "legumes", "legumbre", "legumbres"}),
    ("dairy", "Lácteos", {"dairy", "dairies", "lacteo", "lacteos", "lácteo", "lácteos"}),
    ("tubers", "Tubérculos", {"tuber", "tubers", "tuberculo", "tuberculos", "tubérculo", "tubérculos"}),
    ("fats", "Grasas", {"fat", "fats", "oil", "oils", "grasa", "grasas", "aceite", "aceites"}),
)

AI_OPERATIONAL_STATUSES = [
    AIUsageEvent.Status.ERROR,
    AIUsageEvent.Status.BLOCKED,
]
