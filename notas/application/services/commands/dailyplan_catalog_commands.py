from dataclasses import dataclass

from django.db import transaction

from notas.application.services.commands.dailyplan_commands import save_dailyplan
from notas.domain.models import DailyPlan, DailyPlanCatalogEntry


@dataclass(frozen=True)
class SaveCatalogDailyPlanResult:
    dailyplan: DailyPlan
    already_saved: bool


@transaction.atomic
def save_catalog_dailyplan_to_library(*, entry: DailyPlanCatalogEntry, user) -> SaveCatalogDailyPlanResult:
    existing = (
        DailyPlan.objects.select_for_update()
        .filter(created_by=user, forked_from=entry.dailyplan)
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .order_by("id")
        .first()
    )
    if existing is not None:
        return SaveCatalogDailyPlanResult(dailyplan=existing, already_saved=True)
    return SaveCatalogDailyPlanResult(dailyplan=save_dailyplan(entry.dailyplan, user), already_saved=False)
