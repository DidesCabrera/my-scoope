from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from admin_operations.services import (
    build_account_detail_vm,
    build_accounts_operations_vm,
    build_audit_log_vm,
    build_ai_operations_vm,
    build_ai_proposal_detail_vm,
    build_candidate_detail_vm,
    build_food_catalog_inventory_vm,
    build_food_catalog_imports_vm,
    build_food_catalog_operations_vm,
    build_operations_overview_vm,
    flash_operation_result,
    perform_candidate_operation,
    perform_catalog_food_operation,
    perform_core_seed_apply,
    perform_core_seed_dry_run,
    perform_usda_apply,
    perform_usda_dry_run,
    perform_credit_adjustment,
    perform_ai_proposal_operation,
    perform_ai_quota_operation,
    perform_ai_usage_event_operation,
    perform_credit_reservation_release,
)
from notas.presentation.config.viewmodel_config import ADMIN_OPERATIONS_OVERVIEW_VIEWMODE
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.viewmodels.base_vm import BaseVM


@staff_member_required
def overview(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_operations_overview_vm()
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/overview.html", base_vm.as_context())



@staff_member_required
def audit_log(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_audit_log_vm(query=request.GET.get("q", ""))
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/audit_log.html", base_vm.as_context())


@staff_member_required
def ai_assistant(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_ai_operations_vm(query=request.GET.get("q", ""))
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/ai_assistant.html", base_vm.as_context())


@staff_member_required
@require_POST
def ai_usage_event_action(request, event_id):
    result = perform_ai_usage_event_operation(
        event_id=event_id,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_ai_assistant")


@staff_member_required
@require_POST
def ai_quota_action(request, quota_id):
    result = perform_ai_quota_operation(
        quota_id=quota_id,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_ai_assistant")


@staff_member_required
def ai_proposal_detail(request, proposal_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_ai_proposal_detail_vm(proposal_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/ai_proposal_detail.html", base_vm.as_context())


@staff_member_required
@require_POST
def ai_proposal_action(request, proposal_id):
    result = perform_ai_proposal_operation(
        proposal_id=proposal_id,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_ai_proposal", proposal_id=proposal_id)


@staff_member_required
def accounts(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_accounts_operations_vm(query=request.GET.get("q", ""))
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/accounts.html", base_vm.as_context())


@staff_member_required
def account_detail(request, user_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_account_detail_vm(user_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/account_detail.html", base_vm.as_context())


@staff_member_required
@require_POST
def account_credit_adjustment(request, user_id):
    result = perform_credit_adjustment(
        user_id=user_id,
        actor=request.user,
        credits_delta=request.POST.get("credits_delta", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_account_detail", user_id=user_id)


@staff_member_required
@require_POST
def account_reservation_release(request, user_id, reservation_id):
    result = perform_credit_reservation_release(
        reservation_id=reservation_id,
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_account_detail", user_id=user_id)


@staff_member_required
def food_catalog(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_operations_vm()
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog.html", base_vm.as_context())


@staff_member_required
def food_catalog_inventory(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_inventory_vm(
        query=request.GET.get("q", ""),
        status=request.GET.get("status", ""),
        source_type=request.GET.get("source", ""),
        food_group=request.GET.get("group", ""),
        solver_state=request.GET.get("solver", ""),
        page=request.GET.get("page", 1),
    )
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_inventory.html", base_vm.as_context())


@staff_member_required
def food_catalog_imports(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_imports_vm(
        source_type=request.GET.get("source", ""),
        status=request.GET.get("status", ""),
    )
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_imports.html", base_vm.as_context())


@staff_member_required
@require_POST
def food_catalog_core_seed_dry_run(request):
    result = perform_core_seed_dry_run(actor=request.user, reason=request.POST.get("reason", ""))
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_core_seed_apply(request):
    result = perform_core_seed_apply(
        actor=request.user,
        dry_run_batch_id=request.POST.get("dry_run_batch_id", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_usda_dry_run(request):
    result = perform_usda_dry_run(
        actor=request.user,
        upload=request.FILES.get("file"),
        source_version=request.POST.get("source_version", ""),
        source_dataset=request.POST.get("source_dataset", "foundation_foods"),
        limit=request.POST.get("limit", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_usda_apply(request):
    result = perform_usda_apply(
        actor=request.user,
        upload=request.FILES.get("file"),
        source_version=request.POST.get("source_version", ""),
        source_dataset=request.POST.get("source_dataset", "foundation_foods"),
        limit=request.POST.get("limit", ""),
        dry_run_batch_id=request.POST.get("dry_run_batch_id", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
def food_catalog_candidate_detail(request, candidate_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_candidate_detail_vm(candidate_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_candidate_detail.html", base_vm.as_context())


@staff_member_required
@require_POST
def food_catalog_candidate_action(request, candidate_id):
    result = perform_candidate_operation(
        candidate_id=candidate_id,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_candidate", candidate_id=candidate_id)


@staff_member_required
@require_POST
def food_catalog_food_action(request, catalog_food_id):
    result = perform_catalog_food_operation(
        catalog_food_id=catalog_food_id,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog")
