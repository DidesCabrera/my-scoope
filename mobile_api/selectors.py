from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from accounts.services.profile import build_account_credit_display
from billing.application.services.apple_app_store import get_or_create_apple_app_account_token
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription
from mobile_api.errors import MobileAPIError
from mobile_api.library_actions import library_actions_payload
from notas.application.proposals.contracts import (
    can_apply_proposal,
    proposal_status_label,
    resolve_proposal_intent,
)
from notas.application.queries.calendarization_execution_queries import (
    calendarization_measurement_summary,
    calendarization_progress_summary,
    meal_execution_state_for_day,
    pending_revision_for_calendarization,
)
from notas.application.queries.calendarization_queries import (
    calendarization_history_for_user,
    calendarized_day_for_user,
    current_calendarization_for_user,
    today_for_calendarization,
)
from notas.application.queries.proposal_queries import (
    build_proposal_dto,
    build_proposal_list_item_dto,
    get_available_proposal_queryset,
)
from notas.application.services.cache.dailyplan_summary import get_dailyplan_summary
from notas.application.services.cache.program_summary import get_program_summary
from notas.application.services.food_imports.localized_names import resolve_food_display_name
from notas.application.services.nutrition.body_metrics import get_basic_body_profile
from notas.application.services.nutrition.weight import get_current_weight
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program
from notas.domain.services.nutrition import macro_kcal_distribution
from notas.presentation.proposals.proposal_review_viewmodels import build_proposal_review_vm


def _safe_number(value) -> float:
    return round(float(value or 0), 1)


def _safe_percentage(part, total) -> float:
    if not total or float(total) <= 0:
        return 0.0
    return float(part or 0) / float(total) * 100


def _cached_or_live(entity, cached_name, live_name):
    cached = getattr(entity, cached_name, None)
    return cached if cached is not None else getattr(entity, live_name)


def _calorie_distribution(protein_kcal, carbs_kcal, fat_kcal) -> dict:
    return {key: _safe_number(value) for key, value in macro_kcal_distribution(protein_kcal, carbs_kcal, fat_kcal).items()}


def _library_nutrition_payload(entity, current_weight=None) -> dict:
    allocation = entity.alloc
    protein = _safe_number(entity.protein)
    return {
        "calories": _safe_number(entity.total_kcal),
        "protein": {
            "grams": protein,
            "allocation": _safe_number(allocation.get("protein")),
            "per_kilogram": _safe_number(protein / current_weight) if current_weight and protein else None,
        },
        "carbs": {"grams": _safe_number(entity.carbs), "allocation": _safe_number(allocation.get("carbs"))},
        "fat": {"grams": _safe_number(entity.fat), "allocation": _safe_number(allocation.get("fat"))},
    }


def _empty_library_panel(kind="none") -> dict:
    return {"kind": kind, "foods": [], "meals": [], "weeks": []}


def _creator_name(entity) -> str:
    creator = entity.created_by
    return creator.get_full_name().strip() or creator.username


def _food_panel_item(meal_food) -> dict:
    return {
        "id": f"meal-food:{meal_food.id}",
        "name": resolve_food_display_name(meal_food.food),
        "quantity": _safe_number(meal_food.quantity),
        "quantity_unit": "g",
        "calories": _safe_number(meal_food.total_kcal),
        "calorie_share": _safe_number(meal_food.kcal_share),
        "calorie_distribution": _calorie_distribution(meal_food.kcal_protein, meal_food.kcal_carbs, meal_food.kcal_fat),
        "protein_grams": _safe_number(meal_food.protein),
        "carbs_grams": _safe_number(meal_food.carbs),
        "fat_grams": _safe_number(meal_food.fat),
        "protein_allocation": _safe_number(meal_food.alloc_protein),
        "carbs_allocation": _safe_number(meal_food.alloc_carbs),
        "fat_allocation": _safe_number(meal_food.alloc_fat),
    }


def _meal_panel_item(dailyplan_meal, dailyplan, current_weight=None) -> dict:
    meal = dailyplan_meal.meal
    meal_total_kcal = _cached_or_live(meal, "total_kcal_cached", "total_kcal")
    meal_kcal_protein = _cached_or_live(meal, "kcal_protein_cached", "kcal_protein")
    meal_kcal_carbs = _cached_or_live(meal, "kcal_carbs_cached", "kcal_carbs")
    meal_kcal_fat = _cached_or_live(meal, "kcal_fat_cached", "kcal_fat")
    protein = _safe_number(_cached_or_live(meal, "protein_cached", "protein"))
    return {
        "id": f"dailyplan-meal:{dailyplan_meal.id}",
        "detail_id": meal.id,
        "name": meal.name,
        "time": str(dailyplan_meal.hour) if dailyplan_meal.hour else None,
        "foods": [_food_panel_item(meal_food) for meal_food in meal.meal_food_set.all()],
        "calories": _safe_number(meal_total_kcal),
        "calorie_share": _safe_number(_safe_percentage(meal_total_kcal, dailyplan.total_kcal)),
        "calorie_distribution": _calorie_distribution(meal_kcal_protein, meal_kcal_carbs, meal_kcal_fat),
        "protein_grams": protein,
        "protein_per_kilogram": _safe_number(protein / current_weight) if current_weight and protein else None,
        "carbs_grams": _safe_number(_cached_or_live(meal, "carbs_cached", "carbs")),
        "fat_grams": _safe_number(_cached_or_live(meal, "fat_cached", "fat")),
        "protein_allocation": _safe_number(_safe_percentage(meal_kcal_protein, dailyplan.kcal_protein)),
        "carbs_allocation": _safe_number(_safe_percentage(meal_kcal_carbs, dailyplan.kcal_carbs)),
        "fat_allocation": _safe_number(_safe_percentage(meal_kcal_fat, dailyplan.kcal_fat)),
    }


def _aggregated_food_panel_items(rows, *, id_prefix: str) -> list[dict]:
    return [
        {
            "id": f"{id_prefix}:{row['child']['id']}",
            "name": row["rel"]["name"],
            "quantity": _safe_number(row["rel"]["quantity"]),
            "quantity_unit": row["rel"]["quantity_unit"],
            "calories": _safe_number(row["rel"]["total_kcal"]),
            "calorie_share": _safe_number(row["rel"]["kcal_share"]),
            "calorie_distribution": {
                key: _safe_number(value)
                for key, value in row["rel"]["kcal_distribution"].items()
            },
            "protein_grams": _safe_number(row["rel"]["g_protein"]),
            "carbs_grams": _safe_number(row["rel"]["g_carbs"]),
            "fat_grams": _safe_number(row["rel"]["g_fat"]),
            "protein_allocation": _safe_number(row["rel"]["alloc_protein"]),
            "carbs_allocation": _safe_number(row["rel"]["alloc_carbs"]),
            "fat_allocation": _safe_number(row["rel"]["alloc_fat"]),
        }
        for row in rows
    ]


def _program_week_panel_items(program, current_weight=None) -> list[dict]:
    summary = get_program_summary(program)
    program_total_kcal = summary["program_totals"]["total_kcal"]
    program_days = {
        (program_day.week_number, program_day.day_number): program_day
        for program_day in program.program_dailyplan.all()
    }

    def day_item(week_number, day):
        program_day = program_days.get((week_number, day["day_number"]))
        snapshot = day.get("snapshot")
        nutrition = (
            {
                "calories": _safe_number(snapshot["total_kcal"]),
                "protein": {
                    "grams": _safe_number(snapshot["protein"]),
                    "allocation": _safe_number(snapshot["alloc"]["protein"]),
                    "per_kilogram": _safe_number(snapshot["protein"] / current_weight) if current_weight and snapshot["protein"] else None,
                },
                "carbs": {"grams": _safe_number(snapshot["carbs"]), "allocation": _safe_number(snapshot["alloc"]["carbs"])},
                "fat": {"grams": _safe_number(snapshot["fat"]), "allocation": _safe_number(snapshot["alloc"]["fat"])},
            }
            if snapshot
            else _library_nutrition_payload(program_day.dailyplan, current_weight) if program_day else None
        )
        return {
            "id": f"program-week:{program.id}:{week_number}:day:{day['day_number']}",
            "day_number": day["day_number"],
            "day_label": day["day_label"],
            "dailyplan_id": program_day.dailyplan_id if program_day else None,
            "plan_name": program_day.dailyplan.name if program_day else None,
            "nutrition": nutrition,
            "meals": [
                _meal_panel_item(dailyplan_meal, program_day.dailyplan, current_weight)
                for dailyplan_meal in program_day.dailyplan.dailyplan_meals.all()
            ] if program_day else [],
        }

    return [
        {
            "id": f"program-week:{program.id}:{week['week_number']}",
            "week_number": week["week_number"],
            "days": [day_item(week["week_number"], day) for day in week["days"]],
            "filled_days_count": week["filled_days_count"],
            "meals_count": week["meals_count"],
            "foods_count": week["foods_count"],
            "average_calories": _safe_number(week["averages"]["total_kcal"]),
            "foods": _aggregated_food_panel_items(
                week["foods_aggregation_table"],
                id_prefix=f"program-week-food:{program.id}:{week['week_number']}",
            ),
            "calories": _safe_number(week["totals"]["total_kcal"]),
            "calorie_share": _safe_number(_safe_percentage(week["totals"]["total_kcal"], program_total_kcal)),
            "calorie_distribution": _calorie_distribution(week["totals"]["kcal_protein"], week["totals"]["kcal_carbs"], week["totals"]["kcal_fat"]),
            "protein_grams": _safe_number(week["totals"]["protein"]),
            "carbs_grams": _safe_number(week["totals"]["carbs"]),
            "fat_grams": _safe_number(week["totals"]["fat"]),
            "protein_allocation": _safe_number(week["totals"]["alloc"]["protein"]),
            "carbs_allocation": _safe_number(week["totals"]["alloc"]["carbs"]),
            "fat_allocation": _safe_number(week["totals"]["alloc"]["fat"]),
        }
        for week in summary["weeks"]
    ]


def _library_page(queryset, *, search, offset, limit, builder) -> dict:
    normalized_search = (search or "").strip()[:100] or None
    if normalized_search:
        queryset = queryset.filter(name__icontains=normalized_search)
    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 100)
    total = queryset.count()
    return {
        "items": [builder(item) for item in queryset[safe_offset:safe_offset + safe_limit]],
        "total": total,
        "offset": safe_offset,
        "limit": safe_limit,
        "search": normalized_search,
    }


def library_foods_payload(user, *, search=None, offset=0, limit=30) -> dict:
    current_weight = get_current_weight(user)
    queryset = Food.objects.filter(created_by=user, is_active=True).select_related("created_by").order_by("list_order", "name", "id")
    return _library_page(
        queryset,
        search=search,
        offset=offset,
        limit=limit,
        builder=lambda food: {
            "id": food.id,
            "entity": "food",
            "name": resolve_food_display_name(food),
            "subtitle": "",
            "nutrition": _library_nutrition_payload(food, current_weight),
            "indicators": [{"label": "base nutricional", "value": "100 g"}],
            "panel": _empty_library_panel(),
            "creator": _creator_name(food),
            "created_at": food.created_at,
            "actions": library_actions_payload(food, user, context="list"),
        },
    )


def library_meals_payload(user, *, search=None, offset=0, limit=30) -> dict:
    current_weight = get_current_weight(user)
    queryset = (
        Meal.objects.filter(created_by=user, is_draft=False, dailyplanmeal__isnull=True).select_related("created_by")
        .annotate(library_food_count=Count("meal_food_set", distinct=True))
        .prefetch_related(Prefetch("meal_food_set", queryset=MealFood.objects.select_related("food").order_by("order", "id")))
        .order_by("list_order", "-created_at", "-id")
        .distinct()
    )
    return _library_page(
        queryset,
        search=search,
        offset=offset,
        limit=limit,
        builder=lambda meal: {
            "id": meal.id,
            "entity": "meal",
            "name": meal.name,
            "subtitle": "",
            "nutrition": _library_nutrition_payload(meal, current_weight),
            "indicators": [{"icon": "food", "label": "alimentos", "value": meal.library_food_count}],
            "panel": {**_empty_library_panel("foods"), "foods": [_food_panel_item(meal_food) for meal_food in meal.meal_food_set.all()]},
            "creator": _creator_name(meal),
            "created_at": meal.created_at,
            "actions": library_actions_payload(meal, user, context="list"),
        },
    )


def library_dailyplans_payload(user, *, search=None, offset=0, limit=30) -> dict:
    current_weight = get_current_weight(user)
    queryset = (
        DailyPlan.objects.filter(created_by=user, is_draft=False).select_related("created_by")
        .exclude(source=DailyPlan.SOURCE_PROGRAM)
        .annotate(
            library_meal_count=Count("dailyplan_meals", distinct=True),
            library_food_count=Count("dailyplan_meals__meal__meal_food_set__food", distinct=True),
        )
        .prefetch_related(
            Prefetch(
                "dailyplan_meals__meal__meal_food_set",
                queryset=MealFood.objects.select_related("food").order_by("order", "id"),
            )
        )
        .order_by("list_order", "-created_at", "-id")
    )
    return _library_page(
        queryset,
        search=search,
        offset=offset,
        limit=limit,
        builder=lambda dailyplan: {
            "id": dailyplan.id,
            "entity": "dailyPlan",
            "name": dailyplan.name,
            "subtitle": "",
            "nutrition": _library_nutrition_payload(dailyplan, current_weight),
            "indicators": [
                {"icon": "meal", "label": "comidas", "value": dailyplan.library_meal_count},
                {"icon": "food", "label": "alimentos", "value": dailyplan.library_food_count},
            ],
            "panel": {
                **_empty_library_panel("meals"),
                "meals": [_meal_panel_item(dailyplan_meal, dailyplan, current_weight) for dailyplan_meal in dailyplan.dailyplan_meals.all()],
            },
            "creator": _creator_name(dailyplan),
            "created_at": dailyplan.created_at,
            "actions": library_actions_payload(dailyplan, user, context="list"),
        },
    )


def library_programs_payload(user, *, search=None, offset=0, limit=30) -> dict:
    current_weight = get_current_weight(user)
    queryset = (
        Program.objects.filter(Q(created_by=user) | Q(shares__accepted_by=user, shares__removed=False)).select_related("created_by")
        .annotate(library_day_count=Count("program_dailyplan", distinct=True))
        .prefetch_related("program_dailyplan__dailyplan__dailyplan_meals__meal__meal_food_set__food")
        .order_by("list_order", "-created_at", "-id")
        .distinct()
    )
    return _library_page(
        queryset,
        search=search,
        offset=offset,
        limit=limit,
        builder=lambda program: {
            "id": program.id,
            "entity": "program",
            "name": program.name,
            "subtitle": "",
            "nutrition": _library_nutrition_payload(program, current_weight),
            "indicators": [
                {"icon": "week", "label": "semanas", "value": program.normalized_duration_weeks},
                {"icon": "dailyPlan", "label": "planes asignados", "value": program.library_day_count},
                {"icon": "food", "label": "alimentos", "value": get_program_summary(program)["program_foods_count"]},
            ],
            "panel": {**_empty_library_panel("weeks"), "weeks": _program_week_panel_items(program, current_weight)},
            "creator": _creator_name(program),
            "created_at": program.created_at,
            "can_calendarize": program.created_by_id == user.id,
            "actions": library_actions_payload(program, user, context="list"),
        },
    )


def library_item_detail_payload(user, entity: str, item_id: int) -> dict:
    current_weight = get_current_weight(user)
    if entity == "foods":
        item = Food.objects.filter(pk=item_id, created_by=user, is_active=True).select_related("created_by").first()
        if item:
            return {"id": item.id, "entity": "food", "name": resolve_food_display_name(item), "subtitle": "", "nutrition": _library_nutrition_payload(item, current_weight), "indicators": [{"label": "base nutricional", "value": "100 g"}], "panel": _empty_library_panel(), "creator": _creator_name(item), "created_at": item.created_at, "actions": library_actions_payload(item, user, context="detail")}
    elif entity == "meals":
        item = (Meal.objects.filter(pk=item_id, created_by=user, is_draft=False).select_related("created_by").annotate(library_food_count=Count("meal_food_set", distinct=True)).prefetch_related(Prefetch("meal_food_set", queryset=MealFood.objects.select_related("food").order_by("order", "id"))).first())
        if item:
            return {"id": item.id, "entity": "meal", "name": item.name, "subtitle": "", "nutrition": _library_nutrition_payload(item, current_weight), "indicators": [{"icon": "food", "label": "alimentos", "value": item.library_food_count}], "panel": {**_empty_library_panel("foods"), "foods": [_food_panel_item(row) for row in item.meal_food_set.all()]}, "creator": _creator_name(item), "created_at": item.created_at, "actions": library_actions_payload(item, user, context="detail")}
    elif entity == "daily-plans":
        item = (DailyPlan.objects.filter(pk=item_id, created_by=user, is_draft=False).select_related("created_by").annotate(library_meal_count=Count("dailyplan_meals", distinct=True), library_food_count=Count("dailyplan_meals__meal__meal_food_set__food", distinct=True)).prefetch_related(Prefetch("dailyplan_meals__meal__meal_food_set", queryset=MealFood.objects.select_related("food").order_by("order", "id"))).first())
        if item:
            foods = _aggregated_food_panel_items(
                get_dailyplan_summary(item)["foods_aggregation_table"],
                id_prefix=f"dailyplan-food:{item.id}",
            )
            return {"id": item.id, "entity": "dailyPlan", "name": item.name, "subtitle": "", "nutrition": _library_nutrition_payload(item, current_weight), "indicators": [{"icon": "meal", "label": "comidas", "value": item.library_meal_count}, {"icon": "food", "label": "alimentos", "value": item.library_food_count}], "panel": {**_empty_library_panel("meals"), "meals": [_meal_panel_item(row, item, current_weight) for row in item.dailyplan_meals.all()], "foods": foods}, "creator": _creator_name(item), "created_at": item.created_at, "actions": library_actions_payload(item, user, context="detail")}
    elif entity == "programs":
        item = (Program.objects.filter(pk=item_id).filter(Q(created_by=user) | Q(shares__accepted_by=user, shares__removed=False)).select_related("created_by").annotate(library_day_count=Count("program_dailyplan", distinct=True)).prefetch_related("program_dailyplan__dailyplan__dailyplan_meals__meal__meal_food_set__food").distinct().first())
        if item:
            return {"id": item.id, "entity": "program", "name": item.name, "subtitle": "", "nutrition": _library_nutrition_payload(item, current_weight), "indicators": [{"icon": "week", "label": "semanas", "value": item.normalized_duration_weeks}, {"icon": "dailyPlan", "label": "planes asignados", "value": item.library_day_count}, {"icon": "food", "label": "alimentos", "value": get_program_summary(item)["program_foods_count"]}], "panel": {**_empty_library_panel("weeks"), "weeks": _program_week_panel_items(item, current_weight)}, "creator": _creator_name(item), "created_at": item.created_at, "can_calendarize": item.created_by_id == user.id, "actions": library_actions_payload(item, user, context="detail")}
    raise MobileAPIError(code="library_item_not_found", message="The requested library item was not found.", status_code=404)


def session_payload(auth) -> dict:
    user = auth.user
    display_name = user.get_full_name().strip() or user.username
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": display_name,
        "scopes": list(auth.token.scopes),
        "device_session_id": (
            str(auth.token.device_session.public_id)
            if auth.token.device_session_id
            else None
        ),
    }


def profile_payload(user) -> dict:
    body = get_basic_body_profile(user)
    profile = user.profile
    return {
        "birth_date": body.birth_date,
        "sex": body.sex,
        "height_cm": body.height_cm,
        "timezone_name": profile.timezone_name,
        "onboarding_completed": profile.onboarding_completed_at is not None,
        "onboarding_version": profile.onboarding_version,
        "current_weight_kg": body.current_weight_kg,
        "review_disclosure_required": (
            profile.mobile_disclosure_version != profile.MOBILE_DISCLOSURE_VERSION
            or profile.mobile_disclosure_accepted_at is None
        ),
        "review_disclosure_version": profile.MOBILE_DISCLOSURE_VERSION,
    }


def entitlements_payload(user) -> dict:
    account = build_account_credit_display(user)
    return {
        "plan_name": account.plan_name,
        "plan_slug": account.plan_slug,
        "subscription_status": account.subscription_status,
        "period": account.period,
        "available_credits": account.available_credits,
        "reserved_credits": account.reserved_credits,
        "monthly_credit_limit": account.monthly_credit_limit,
        "daily_credit_limit": account.daily_credit_limit,
    }


def subscription_payload(user, *, purchases_enabled: bool) -> dict:
    profile = getattr(user, "profile", None)
    eligible = str(getattr(profile, "role", "member") or "member").lower() == "member"
    subscription = getattr(user, "account_subscription", None)
    token = get_or_create_apple_app_account_token(user) if eligible else None
    products = []
    if eligible and purchases_enabled:
        products = [
            {
                "product_id": product.external_product_id,
                "plan_name": product.account_plan.name,
                "interval": product.interval,
            }
            for product in BillingProduct.objects.select_related("account_plan").filter(
                provider=PaymentProvider.APPLE_APP_STORE,
                active=True,
                account_plan__status="active",
            )
        ]
    evidence = list(
        ProviderSubscription.objects.filter(user=user)
        .exclude(status=ProviderSubscription.Status.PENDING)
        .order_by("provider", "-updated_at")
        .values("provider", "status", "current_period_end")
    )
    metadata = dict(getattr(subscription, "metadata", {}) or {})
    return {
        "eligible": eligible,
        "purchases_enabled": bool(eligible and purchases_enabled and products),
        "app_account_token": str(token.token) if token is not None else "",
        "plan_name": subscription.plan.name if subscription is not None else "Sin plan",
        "status": subscription.status if subscription is not None else "none",
        "products": products,
        "evidence": [
            {
                "provider": item["provider"],
                "status": item["status"],
                "period_end": item["current_period_end"],
            }
            for item in evidence
        ],
        "duplicate_active_providers": bool(metadata.get("billing_duplicate_active_providers")),
    }


def today_payload(user, *, now=None) -> dict:
    calendarization = current_calendarization_for_user(user)
    if calendarization is None:
        timezone_name = getattr(user.profile, "timezone_name", "UTC") or "UTC"
        try:
            user_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            user_timezone = ZoneInfo("UTC")
        local_date = timezone.localdate(now or timezone.now(), timezone=user_timezone)
        return {
            "local_date": local_date,
            "calendarization": None,
            "day_id": None,
            "has_plan": False,
            "plan_snapshot": None,
            "meal_execution": [],
            "adherence": None,
            "measurements": None,
            "reminders": None,
            "pending_revision": None,
        }

    local_date = today_for_calendarization(calendarization, now=now)
    day = next((item for item in calendarization.days.all() if item.calendar_date == local_date), None)
    total_days = max(1, (calendarization.end_date - calendarization.start_date).days + 1)
    progress_day = min(max((local_date - calendarization.start_date).days + 1, 0), total_days)
    elapsed_end = min(local_date, calendarization.end_date)
    period_start = max(calendarization.start_date, elapsed_end - timedelta(days=6))
    return {
        "local_date": local_date,
        "calendarization": {
            "id": calendarization.id,
            "program_name": calendarization.program_name_snapshot,
            "status": calendarization.status,
            "start_date": calendarization.start_date,
            "end_date": calendarization.end_date,
            "timezone_name": calendarization.timezone_name,
            "progress_day": progress_day,
            "progress_total_days": total_days,
            "progress_percent": round((progress_day / total_days) * 100),
        },
        "day_id": day.id if day else None,
        "has_plan": bool(day and day.has_plan),
        "plan_snapshot": (
            _calendarized_snapshot_with_meal_links(user, day.plan_snapshot)
            if day and day.has_plan
            else None
        ),
        "meal_execution": meal_execution_state_for_day(day) if day and day.has_plan else [],
        "adherence": (
            calendarization_progress_summary(
                calendarization,
                period_start=period_start,
                period_end=elapsed_end,
            )
            if elapsed_end >= calendarization.start_date
            else None
        ),
        "measurements": calendarization_measurement_summary(calendarization),
        "reminders": reminder_settings_payload(calendarization),
        "pending_revision": revision_payload(pending_revision_for_calendarization(calendarization)),
    }


def reminder_settings_payload(calendarization) -> dict:
    upcoming = [
        {
            "event_key": event.event_key,
            "event_type": event.event_type,
            "meal_key": event.meal_snapshot_key,
            "local_date": event.local_scheduled_date,
            "local_time": event.local_scheduled_time,
            "scheduled_for_utc": event.scheduled_for_utc,
            "status": event.status,
        }
        for event in calendarization.notification_events.filter(status="pending").order_by(
            "scheduled_for_utc", "id"
        )[:20]
    ]
    return {
        "timezone_name": calendarization.timezone_name,
        "daily_notification_time": calendarization.daily_notification_time,
        "daily_notifications_enabled": calendarization.daily_notifications_enabled,
        "meal_notifications_enabled": calendarization.meal_notifications_enabled,
        "upcoming": upcoming,
    }


def revision_payload(revision) -> dict | None:
    if revision is None:
        return None
    before_by_date = {
        item.get("calendar_date"): item
        for item in revision.before_snapshot.get("days", [])
    }
    days = []
    for after in revision.after_snapshot.get("days", []):
        calendar_date = after.get("calendar_date")
        before = before_by_date.get(calendar_date, {})
        before_plan = before.get("plan_snapshot") or {}
        after_plan = after.get("plan_snapshot") or {}
        days.append(
            {
                "calendar_date": calendar_date,
                "before_name": before_plan.get("name", ""),
                "after_name": after_plan.get("name", ""),
                "before_totals": before_plan.get("totals", {}),
                "after_totals": after_plan.get("totals", {}),
            }
        )
    return {
        "id": revision.id,
        "effective_from": revision.effective_from,
        "status": revision.status,
        "rationale": revision.rationale,
        "days": days,
        "created_at": revision.created_at,
    }


def review_payload(review) -> dict:
    return {
        "id": review.id,
        "period_start": review.period_start,
        "period_end": review.period_end,
        "energy_score": review.energy_score,
        "hunger_score": review.hunger_score,
        "training_performance_score": review.training_performance_score,
        "note": review.note,
        "summary_snapshot": review.summary_snapshot,
        "created_at": review.created_at,
    }


def food_label_capture_payload(result) -> dict:
    food = result.food
    receipt = result.receipt
    return {
        "id": food.id,
        "name": food.name,
        "protein_g": food.protein,
        "carbs_g": food.carbs,
        "fat_g": food.fat,
        "saturated_fat_g": float(food.saturated_fat_g_per_100g) if food.saturated_fat_g_per_100g is not None else None,
        "sugar_g": float(food.sugar_g_per_100g) if food.sugar_g_per_100g is not None else None,
        "fiber_g": float(food.fiber_g_per_100g) if food.fiber_g_per_100g is not None else None,
        "sodium_mg": float(food.sodium_mg_per_100g) if food.sodium_mg_per_100g is not None else None,
        "total_kcal": food.total_kcal,
        "is_user_food": food.created_by_id is not None and not food.is_global,
        "is_verified": food.is_verified,
        "capture_receipt_id": receipt.id,
        "detected_basis": receipt.detected_basis,
        "serving_size_g": float(receipt.serving_size_g) if receipt.serving_size_g is not None else None,
        "ocr_engine": receipt.ocr_engine,
        "created_at": receipt.created_at,
    }


def _calendarization_data_payload(calendarization) -> dict:
    local_date = today_for_calendarization(calendarization)
    total_days = max(1, (calendarization.end_date - calendarization.start_date).days + 1)
    progress_day = min(max((local_date - calendarization.start_date).days + 1, 0), total_days)
    return {
        "id": calendarization.id,
        "source_program_id": calendarization.source_program_id,
        "program_name": calendarization.program_name_snapshot,
        "status": calendarization.status,
        "start_date": calendarization.start_date,
        "end_date": calendarization.end_date,
        "timezone_name": calendarization.timezone_name,
        "progress_day": progress_day,
        "progress_total_days": total_days,
        "progress_percent": round((progress_day / total_days) * 100),
    }


def _calendarized_days_payload(calendarization) -> list[dict]:
    return [
        {
            "id": day.id,
            "calendar_date": day.calendar_date,
            "week_number": day.week_number,
            "day_number": day.day_number,
            "has_plan": day.has_plan,
            "plan_name": (day.plan_snapshot or {}).get("name", ""),
        }
        for day in calendarization.days.all()
    ]


def active_program_payload(user) -> dict:
    calendarization = current_calendarization_for_user(user)
    if calendarization is None:
        return {"calendarization": None, "days": [], "adherence": None, "indicators": []}
    local_date = today_for_calendarization(calendarization)
    adherence = (
        calendarization_progress_summary(
            calendarization,
            period_start=calendarization.start_date,
            period_end=min(local_date, calendarization.end_date),
        )
        if local_date >= calendarization.start_date
        else None
    )
    source_program = calendarization.source_program
    indicators = [
        {
            "icon": "week",
            "label": "semanas",
            "value": source_program.normalized_duration_weeks if source_program else max(1, ((calendarization.end_date - calendarization.start_date).days + 7) // 7),
        },
        {
            "icon": "dailyPlan",
            "label": "planes asignados",
            "value": source_program.filled_days_count if source_program else sum(1 for day in calendarization.days.all() if day.has_plan),
        },
        {
            "icon": "food",
            "label": "alimentos",
            "value": get_program_summary(source_program)["program_foods_count"] if source_program else 0,
        },
    ]
    return {
        "calendarization": _calendarization_data_payload(calendarization),
        "days": _calendarized_days_payload(calendarization),
        "adherence": adherence,
        "indicators": indicators,
    }


def calendarization_history_payload(user, *, limit=20) -> dict:
    safe_limit = min(max(int(limit or 20), 1), 50)
    full_queryset = calendarization_history_for_user(user, limit=None)
    count = full_queryset.count()
    history = list(full_queryset[:safe_limit])
    return {
        "items": [
            {
                "id": calendarization.id,
                "program_name": calendarization.program_name_snapshot,
                "status": calendarization.status,
                "start_date": calendarization.start_date,
                "end_date": calendarization.end_date,
                "timezone_name": calendarization.timezone_name,
                "days_total": len(calendarization.days.all()),
                "days_with_plan": sum(1 for day in calendarization.days.all() if day.has_plan),
                "created_at": calendarization.created_at,
            }
            for calendarization in history
        ],
        "count": count,
    }


def _calendarized_snapshot_with_meal_links(user, snapshot: dict | None) -> dict | None:
    if not snapshot:
        return None
    payload = deepcopy(snapshot)
    meals = payload.get("meals")
    if not isinstance(meals, list):
        return payload

    meals_by_slot_id = {}
    for meal in meals:
        if not isinstance(meal, dict):
            continue
        meal.pop("detail_id", None)
        key = meal.get("key")
        if not isinstance(key, str) or not key.startswith("dailyplan_meal:"):
            continue
        try:
            meals_by_slot_id[int(key.removeprefix("dailyplan_meal:"))] = meal
        except ValueError:
            continue

    links = DailyPlanMeal.objects.filter(
        pk__in=meals_by_slot_id,
        meal__created_by=user,
        meal__is_draft=False,
    ).values_list("id", "meal_id")
    for slot_id, meal_id in links:
        meals_by_slot_id[slot_id]["detail_id"] = meal_id
    return payload


def calendarized_day_payload(user, day_id: int) -> dict | None:
    day = calendarized_day_for_user(user, day_id)
    if day is None:
        return None
    snapshot = _calendarized_snapshot_with_meal_links(user, day.plan_snapshot)
    return {
        "id": day.id,
        "calendar_date": day.calendar_date,
        "week_number": day.week_number,
        "day_number": day.day_number,
        "has_plan": day.has_plan,
        "plan_name": (snapshot or {}).get("name", ""),
        "plan_snapshot": snapshot,
    }


def _proposal_actions(*, status: str, intent: str | None, applied_at=None) -> list[dict]:
    if status == "pending_review":
        return [
            {"key": "approve", "label": "Aprobar", "tone": "default", "requires_confirmation": True},
            {"key": "reject", "label": "Rechazar", "tone": "danger", "requires_confirmation": True},
            {"key": "cancel", "label": "Cancelar", "tone": "danger", "requires_confirmation": True},
        ]
    if can_apply_proposal(status=status, intent=intent, applied_at=applied_at):
        return [
            {"key": "apply", "label": "Aplicar", "tone": "default", "requires_confirmation": True},
            {"key": "cancel", "label": "Cancelar", "tone": "danger", "requires_confirmation": True},
        ]
    if status in {"draft", "approved"}:
        return [{"key": "cancel", "label": "Cancelar", "tone": "danger", "requires_confirmation": True}]
    return []


def _proposal_summary_payload(dto: dict) -> dict:
    intent = resolve_proposal_intent(dto.get("proposed_payload"))
    return {
        "id": dto["id"],
        "title": dto.get("title", ""),
        "summary": dto.get("summary", ""),
        "status": dto.get("status", "draft"),
        "status_label": proposal_status_label(dto.get("status", "")),
        "source": dto.get("source", ""),
        "attachment_kind": dto.get("attachment_kind", "dailyplan"),
        "attachment_label": dto.get("attachment_label", ""),
        "attachment_name": dto.get("attachment_name", ""),
        "is_reviewable": bool(dto.get("is_reviewable")),
        "created_at": dto.get("created_at"),
        "actions": _proposal_actions(
            status=dto.get("status", ""),
            intent=intent,
            applied_at=dto.get("applied_at"),
        ),
    }


def proposal_list_payload(user, *, status_filter=None, offset=0, limit=30) -> dict:
    queryset = get_available_proposal_queryset(user)
    pending_count = queryset.filter(status="pending_review").count()
    allowed_filters = {"pending_review", "approved", "applied", "rejected", "cancelled"}
    if status_filter in allowed_filters:
        queryset = queryset.filter(status=status_filter)
    safe_offset = max(int(offset or 0), 0)
    safe_limit = min(max(int(limit or 30), 1), 50)
    total = queryset.count()
    items = [
        _proposal_summary_payload({
            **build_proposal_list_item_dto(proposal).as_dict(),
            "proposed_payload": proposal.proposed_payload,
            "applied_at": proposal.applied_at,
        })
        for proposal in queryset[safe_offset:safe_offset + safe_limit]
    ]
    return {"items": items, "total": total, "offset": safe_offset, "limit": safe_limit, "pending_count": pending_count}


def _fact_label(value: str) -> str:
    labels = {
        "total_kcal": "Calorías",
        "protein": "Proteína",
        "protein_g": "Proteína",
        "carbs": "Carbohidratos",
        "carbs_g": "Carbohidratos",
        "fat": "Grasas",
        "fat_g": "Grasas",
        "is_valid": "Validación",
        "intent": "Tipo",
    }
    return labels.get(value, value.replace("_", " ").strip().capitalize())


def _bounded_facts(value, *, prefix="", limit=20) -> list[dict]:
    facts: list[dict] = []

    def visit(candidate, path: str) -> None:
        if len(facts) >= limit:
            return
        if isinstance(candidate, dict):
            for key, child in candidate.items():
                if key in {"subject_context", "suggested_changes", "foods", "meals"}:
                    continue
                visit(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(candidate, (str, int, float, bool)) and path:
            key = path.split(".")[-1]
            display = "Sí" if candidate is True else "No" if candidate is False else str(candidate)
            facts.append({"label": _fact_label(key), "value": display})

    visit(value, prefix)
    return facts


def _proposal_kpis_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {key: value.get(key) for key in ("total_kcal", "protein", "carbs", "fat", "ppk")}


def _proposal_meal_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {
        "name": value.get("name", ""),
        "foods": [
            {
                "food_id": food.get("food_id"),
                "food_name": food.get("food_name", ""),
                "quantity": food.get("quantity"),
                "unit": food.get("unit", "g"),
            }
            for food in value.get("foods", [])
            if isinstance(food, dict)
        ],
        "kpis": _proposal_kpis_payload(value.get("kpis")),
    }


def _proposal_dailyplan_payload(value) -> dict | None:
    if not isinstance(value, dict):
        return None
    return {
        "name": value.get("name", ""),
        "meals": [
            {
                "hour": item.get("hour"),
                "note": item.get("note", ""),
                "meal": _proposal_meal_payload(item.get("meal")),
            }
            for item in value.get("meals", [])
            if isinstance(item, dict) and isinstance(item.get("meal"), dict)
        ],
        "kpis": _proposal_kpis_payload(value.get("kpis")),
    }


def proposal_detail_payload(user, proposal_id: int) -> dict | None:
    proposal = get_available_proposal_queryset(user).filter(pk=proposal_id).first()
    if proposal is None:
        return None
    dto = build_proposal_dto(proposal).as_dict()
    review = build_proposal_review_vm(dto).as_dict()
    summary = _proposal_summary_payload({**dto, **build_proposal_list_item_dto(proposal).as_dict()})
    warning = review["subject_context_warning"]
    applied = review.get("applied_result")
    return {
        **summary,
        "dailyplan_id": dto.get("dailyplan_id"),
        "dailyplan_name": dto.get("dailyplan_name", ""),
        "created_by_username": dto.get("created_by_username", ""),
        "reviewed_by_username": dto.get("reviewed_by_username"),
        "intent": review["payload"].get("intent"),
        "entity_title": review["payload"].get("entity_title", ""),
        "target_facts": _bounded_facts(dto.get("targets", {})),
        "current_facts": _bounded_facts(dto.get("current_snapshot", {}).get("actual", dto.get("current_snapshot", {}))),
        "validation_facts": _bounded_facts(dto.get("validation_summary", {}).get("payload_validation", {})),
        "meal": _proposal_meal_payload(review["payload"].get("meal")),
        "dailyplan": _proposal_dailyplan_payload(review["payload"].get("dailyplan")),
        "subject_context_warning": {
            "requires_warning": warning.get("requires_warning", False),
            "source_label": warning.get("source_label", ""),
            "calculation_weight_label": warning.get("calculation_weight_label", ""),
            "title": warning.get("title", ""),
            "message": warning.get("message", ""),
        },
        "applied_result": ({"kind": applied.get("kind"), "object_id": applied.get("object_id"), "object_name": applied.get("object_name", "")} if applied else None),
        "applied_at": dto.get("applied_at"),
    }
