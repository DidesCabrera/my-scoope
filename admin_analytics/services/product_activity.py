from __future__ import annotations

from decimal import Decimal

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.product_activity import get_product_activity_metrics
from admin_analytics.viewmodels import (
    AdminAnalyticsHealthSignalVM,
    AdminAnalyticsKpiVM,
    AdminAnalyticsProductActivityVM,
    AdminAnalyticsProductBuilderRowVM,
    AdminAnalyticsProductComparisonRowVM,
    AdminAnalyticsProductEntityRowVM,
    AdminAnalyticsProductShareRowVM,
    AdminAnalyticsProductSourceRowVM,
    AdminAnalyticsProgramWeekRowVM,
    AdminAnalyticsSectionVM,
)


def _format_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _format_decimal(value, digits: int = 1) -> str:
    amount = Decimal(str(value or 0))
    return f"{amount:.{digits}f}".replace(".", ",")


def _format_label(value, fallback: str = "Sin dato") -> str:
    text = str(value or "").strip()
    return text or fallback


def _format_ratio(numerator, denominator) -> str:
    denominator = int(denominator or 0)
    if denominator <= 0:
        return "0%"
    ratio = Decimal(int(numerator or 0)) / Decimal(denominator) * Decimal("100")
    return f"{ratio:.0f}%"


def build_product_activity_vm(analytics_filters: AdminAnalyticsFilters | None = None) -> AdminAnalyticsProductActivityVM:
    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    metrics = get_product_activity_metrics(analytics_filters=analytics_filters)
    entities = metrics["entities"]
    composition = metrics["composition"]
    comparisons = metrics["comparisons"]
    shares = metrics["shares"]
    proposals = metrics["proposals"]
    north_star = metrics["north_star"]

    meals = entities["meals"]
    dailyplans = entities["dailyplans"]
    programs = entities["programs"]
    foods = entities["foods"]

    sections = [
        AdminAnalyticsSectionVM(
            title="Actividad nutricional",
            description="Creación reciente de las entidades operacionales principales de notas.",
            kpis=[
                AdminAnalyticsKpiVM("Builders 7d", _format_int(north_star["weekly_active_nutrition_builders"]), "Weekly Active Nutrition Builders"),
                AdminAnalyticsKpiVM("Meals 7d", _format_int(meals["created_7d"]), f"Total: {_format_int(meals['total'])}"),
                AdminAnalyticsKpiVM("DailyPlans 7d", _format_int(dailyplans["created_7d"]), f"Total: {_format_int(dailyplans['total'])}"),
                AdminAnalyticsKpiVM("Programs 7d", _format_int(programs["created_7d"]), f"Total: {_format_int(programs['total'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Composición nutricional",
            description="Señales de profundidad: foods por meal, meals por plan y días llenos por programa.",
            kpis=[
                AdminAnalyticsKpiVM("MealFoods", _format_int(composition["meal_foods_total"]), f"Promedio/Meal: {_format_decimal(meals['avg_foods_per_meal'])}"),
                AdminAnalyticsKpiVM("DailyPlanMeals", _format_int(composition["dailyplan_meals_total"]), f"Promedio/Plan: {_format_decimal(dailyplans['avg_meals_per_dailyplan'])}"),
                AdminAnalyticsKpiVM("ProgramDays", _format_int(composition["program_days_total"]), f"Promedio/Programa: {_format_decimal(programs['avg_filled_days_per_program'])}"),
                AdminAnalyticsKpiVM("Programas con semanas", _format_int(programs["with_slots"]), f"Multi-semana: {_format_int(programs['with_multiple_weeks'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Compartir y reutilizar",
            description="Shares, comparaciones y forks/duplicados como señales de reutilización del producto.",
            kpis=[
                AdminAnalyticsKpiVM("Shares 7d", _format_int(shares["sent_7d"]), f"Total: {_format_int(shares['total'])}"),
                AdminAnalyticsKpiVM("Shares aceptados", _format_int(shares["accepted_total"]), f"Unread inbox: {_format_int(shares['unread_total'])}"),
                AdminAnalyticsKpiVM("Comparaciones 7d", _format_int(comparisons["updated_7d"]), f"Total: {_format_int(comparisons['total'])}"),
                AdminAnalyticsKpiVM("Propuestas aplicadas 7d", _format_int(proposals["applied_7d"]), f"Creadas: {_format_int(proposals['created_7d'])}"),
            ],
        ),
        AdminAnalyticsSectionVM(
            title="Foods operativos",
            description="Lectura liviana de Food en notas. La calidad profunda se separa para ADM06/Food Catalog.",
            kpis=[
                AdminAnalyticsKpiVM("Foods totales", _format_int(foods["total"]), f"Activos: {_format_int(foods['active'])}"),
                AdminAnalyticsKpiVM("Foods 7d / 30d", f"{_format_int(foods['created_7d'])}/{_format_int(foods['created_30d'])}", "Creados recientemente"),
                AdminAnalyticsKpiVM("Globales", _format_int(foods["global"]), "Disponibles para todos"),
                AdminAnalyticsKpiVM("Verificados", _format_int(foods["verified"]), "is_verified=True"),
            ],
        ),
    ]

    draft_total = meals["draft"] + dailyplans["draft"] + programs["draft"]
    total_core_entities = meals["total"] + dailyplans["total"] + programs["total"]
    composition_depth = composition["meal_foods_total"] + composition["dailyplan_meals_total"] + composition["program_days_total"]

    health_signals = [
        AdminAnalyticsHealthSignalVM(
            label="Activación nutricional",
            status="healthy" if north_star["weekly_active_nutrition_builders"] else "watch",
            value=_format_int(north_star["weekly_active_nutrition_builders"]),
            description="Usuarios con acciones nutricionales significativas en los últimos 7 días.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Draft pressure",
            status="watch" if total_core_entities and (draft_total / total_core_entities) > 0.5 else "healthy",
            value=_format_ratio(draft_total, total_core_entities),
            description="Proporción de Meals/DailyPlans/Programs aún en draft.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Composición",
            status="healthy" if composition_depth else "watch",
            value=_format_int(composition_depth),
            description="Relaciones MealFood + DailyPlanMeal + ProgramDay existentes.",
        ),
        AdminAnalyticsHealthSignalVM(
            label="Sharing",
            status="healthy" if shares["sent_7d"] else "watch",
            value=_format_int(shares["sent_7d"]),
            description="Shares enviados durante el período inicial.",
        ),
    ]

    entity_rows = [
        AdminAnalyticsProductEntityRowVM(
            entity="Foods",
            total=_format_int(foods["total"]),
            created_7d=_format_int(foods["created_7d"]),
            created_30d=_format_int(foods["created_30d"]),
            draft="—",
            public="—",
            forked="—",
            usage=f"Activos {_format_int(foods['active'])} · Verificados {_format_int(foods['verified'])}",
        ),
        AdminAnalyticsProductEntityRowVM(
            entity="Meals",
            total=_format_int(meals["total"]),
            created_7d=_format_int(meals["created_7d"]),
            created_30d=_format_int(meals["created_30d"]),
            draft=_format_int(meals["draft"]),
            public=_format_int(meals["public"]),
            forked=_format_int(meals["forked"]),
            usage=f"Con foods {_format_int(meals['with_foods'])} · Avg {_format_decimal(meals['avg_foods_per_meal'])}",
        ),
        AdminAnalyticsProductEntityRowVM(
            entity="DailyPlans",
            total=_format_int(dailyplans["total"]),
            created_7d=_format_int(dailyplans["created_7d"]),
            created_30d=_format_int(dailyplans["created_30d"]),
            draft=_format_int(dailyplans["draft"]),
            public=_format_int(dailyplans["public"]),
            forked=_format_int(dailyplans["forked"]),
            usage=f"Con meals {_format_int(dailyplans['with_meals'])} · Avg {_format_decimal(dailyplans['avg_meals_per_dailyplan'])}",
        ),
        AdminAnalyticsProductEntityRowVM(
            entity="Programs",
            total=_format_int(programs["total"]),
            created_7d=_format_int(programs["created_7d"]),
            created_30d=_format_int(programs["created_30d"]),
            draft=_format_int(programs["draft"]),
            public=_format_int(programs["public"]),
            forked=_format_int(programs["forked"]),
            usage=f"Con slots {_format_int(programs['with_slots'])} · Multi-semana {_format_int(programs['with_multiple_weeks'])}",
        ),
    ]

    source_rows = [
        AdminAnalyticsProductSourceRowVM(
            source=_format_label(row["source"]),
            total=_format_int(row["total"]),
            created_7d=_format_int(row["created_7d"]),
        )
        for row in composition["dailyplan_source_rows"]
    ]

    comparison_rows = [
        AdminAnalyticsProductComparisonRowVM(
            kind=_format_label(row["kind"]),
            total=_format_int(row["total"]),
            updated_7d=_format_int(row["updated_7d"]),
            owners=_format_int(row["owners"]),
        )
        for row in comparisons["rows"]
    ]

    share_rows = [
        AdminAnalyticsProductShareRowVM(
            label=row["label"],
            sent_total=_format_int(row["sent_total"]),
            sent_7d=_format_int(row["sent_7d"]),
            sent_30d=_format_int(row["sent_30d"]),
            accepted_total=_format_int(row["accepted_total"]),
            unread_total=_format_int(row["unread_total"]),
            favorite_total=_format_int(row["favorite_total"]),
            removed_total=_format_int(row["removed_total"]),
        )
        for row in shares["rows"]
    ]

    builder_rows = [
        AdminAnalyticsProductBuilderRowVM(
            email=row["email"],
            username=row["username"],
            meals=_format_int(row["meals"]),
            dailyplans=_format_int(row["dailyplans"]),
            programs=_format_int(row["programs"]),
            shares=_format_int(row["shares"]),
            comparisons=_format_int(row["comparisons"]),
            applied_proposals=_format_int(row["applied_proposals"]),
            score=_format_int(row["score"]),
        )
        for row in north_star["top_builder_rows"]
    ]

    program_week_rows = [
        AdminAnalyticsProgramWeekRowVM(
            week_number=_format_int(row["week_number"]),
            slots=_format_int(row["slots"]),
            programs=_format_int(row["programs"]),
        )
        for row in composition["program_week_rows"]
    ]

    return AdminAnalyticsProductActivityVM(
        title="Product Activity Analytics",
        subtitle="Métricas read-only de actividad nutricional en notas: Meals, DailyPlans, Programs, shares, comparaciones y propuestas.",
        generated_at=metrics["generated_at"],
        period_label=metrics["period_label"],
        filters=analytics_filters.as_template_context(),
        sections=sections,
        health_signals=health_signals,
        entity_rows=entity_rows,
        source_rows=source_rows,
        comparison_rows=comparison_rows,
        share_rows=share_rows,
        builder_rows=builder_rows,
        program_week_rows=program_week_rows,
    )
