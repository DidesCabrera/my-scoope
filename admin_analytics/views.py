from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from admin_analytics.filters import AdminAnalyticsFilters
from admin_analytics.services.accounts import build_accounts_vm
from admin_analytics.services.ai_assistant import build_ai_assistant_vm
from admin_analytics.services.alerts import build_alerts_vm
from admin_analytics.services.food_catalog import build_food_catalog_vm
from admin_analytics.services.nutrition_solver import build_nutrition_solver_vm
from admin_analytics.services.overview import build_overview_vm
from admin_analytics.services.product_activity import build_product_activity_vm
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import ADMIN_ANALYTICS_OVERVIEW_VIEWMODE
from notas.presentation.viewmodels.base_vm import BaseVM


@staff_member_required
def overview(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_overview_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/overview.html", base_vm.as_context())


@staff_member_required
def accounts(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_accounts_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/accounts.html", base_vm.as_context())


@staff_member_required
def ai_assistant(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_ai_assistant_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/ai_assistant.html", base_vm.as_context())



@staff_member_required
def product_activity(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_product_activity_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/product_activity.html", base_vm.as_context())


@staff_member_required
def food_catalog(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_food_catalog_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/food_catalog.html", base_vm.as_context())


@staff_member_required
def nutrition_solver(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_nutrition_solver_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/nutrition_solver.html", base_vm.as_context())


@staff_member_required
def alerts(request):
    ui_vm = build_ui_vm(ADMIN_ANALYTICS_OVERVIEW_VIEWMODE)
    analytics_filters = AdminAnalyticsFilters.from_querydict(request.GET)
    content = build_alerts_vm(analytics_filters=analytics_filters)

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_analytics/alerts.html", base_vm.as_context())
