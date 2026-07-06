from __future__ import annotations

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.selectors.accounts import get_account_metrics
from admin_analytics.selectors.ai_assistant import get_ai_assistant_metrics
from admin_analytics.selectors.food_catalog import get_food_catalog_metrics
from admin_analytics.selectors.nutrition_solver import get_nutrition_solver_metrics
from admin_analytics.selectors.product_activity import get_product_activity_metrics


def get_alert_metrics(*, now=None, analytics_filters: AdminAnalyticsFilters | None = None) -> dict:
    """Return cross-domain inputs for ADM09 internal health alerts.

    Alerts are derived from existing reporting selectors. This keeps ADM09
    read-only and avoids adding analytical tables before the product needs
    historical alert snapshots.
    """

    analytics_filters = analytics_filters or AdminAnalyticsFilters()
    product = get_product_activity_metrics(now=now, analytics_filters=analytics_filters)
    ai = get_ai_assistant_metrics(now=now, analytics_filters=analytics_filters)
    accounts = get_account_metrics(now=now, analytics_filters=analytics_filters)
    food_catalog = get_food_catalog_metrics(now=now, analytics_filters=analytics_filters)
    solver = get_nutrition_solver_metrics(now=now, analytics_filters=analytics_filters)

    return {
        "generated_at": product["generated_at"],
        "period_label": analytics_filters.period_label,
        "product": product,
        "ai": ai,
        "accounts": accounts,
        "food_catalog": food_catalog,
        "solver": solver,
    }
