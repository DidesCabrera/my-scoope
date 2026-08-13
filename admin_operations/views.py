from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from admin_operations.interface_feedback import flash_operation_result, operation_not_found_as_404
from admin_operations.services import (
    build_account_detail_vm,
    build_accounts_operations_vm,
    build_ai_operations_vm,
    build_ai_proposal_detail_vm,
    build_audit_log_vm,
    build_candidate_detail_vm,
    build_catalog_food_detail_vm,
    build_food_catalog_data_coverage_vm,
    build_food_catalog_imports_vm,
    build_food_catalog_inventory_vm,
    build_food_catalog_operations_vm,
    build_food_catalog_readiness_vm,
    build_operations_overview_vm,
    build_readiness_batch_detail_vm,
    perform_ai_proposal_operation,
    perform_ai_quota_operation,
    perform_ai_usage_event_operation,
    perform_backfill_apply,
    perform_backfill_dry_run,
    perform_brand_apply,
    perform_brand_dry_run,
    perform_candidate_operation,
    perform_catalog_food_bulk_review,
    perform_catalog_food_operation,
    perform_catalog_food_snapshot,
    perform_catalog_readiness_batch_operation,
    perform_core_seed_apply,
    perform_core_seed_dry_run,
    perform_credit_adjustment,
    perform_credit_reservation_release,
    perform_import_source_policy_operation,
    perform_manual_apply,
    perform_manual_dry_run,
    perform_source_portion_backfill_operation,
    perform_usda_apply,
    perform_usda_dry_run,
    prepare_catalog_readiness_operation,
)
from admin_operations.system_control import build_system_control_vm
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import ADMIN_OPERATIONS_OVERVIEW_VIEWMODE
from notas.presentation.viewmodels.base_vm import BaseVM


@staff_member_required
def overview(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_operations_overview_vm()
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/overview.html", base_vm.as_context())


@staff_member_required
@require_GET
def system_control(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_system_control_vm()
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/system_control.html", base_vm.as_context())



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
@operation_not_found_as_404
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
@operation_not_found_as_404
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
@operation_not_found_as_404
def ai_proposal_detail(request, proposal_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_ai_proposal_detail_vm(proposal_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/ai_proposal_detail.html", base_vm.as_context())


@staff_member_required
@require_POST
@operation_not_found_as_404
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
@operation_not_found_as_404
def account_detail(request, user_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_account_detail_vm(user_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/account_detail.html", base_vm.as_context())


@staff_member_required
@require_POST
@operation_not_found_as_404
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
@operation_not_found_as_404
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
    content = build_food_catalog_operations_vm(
        query=request.GET.get("q", ""),
        stage=request.GET.get("stage", "all"),
        sort=request.GET.get("sort", "quality_asc"),
    )
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog.html", base_vm.as_context())


@staff_member_required
def food_catalog_curation_dashboard(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_operations_vm(
        query=request.GET.get("q", ""),
        stage=request.GET.get("stage", "all"),
        sort=request.GET.get("sort", "quality_asc"),
    )
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_curation_dashboard.html", base_vm.as_context())


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
def food_catalog_inventory_master(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_inventory_vm(
        query=request.GET.get("q", ""),
        status=request.GET.get("status", ""),
        source_type=request.GET.get("source", ""),
        food_group=request.GET.get("group", ""),
        solver_state=request.GET.get("solver", ""),
        section=request.GET.get("section", "identity"),
        page=request.GET.get("page", 1),
    )
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_inventory_master.html", base_vm.as_context())


@staff_member_required
def food_catalog_data_coverage(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_data_coverage_vm(
        section=request.GET.get("section", "identity"),
    )
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_data_coverage.html", base_vm.as_context())


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
def food_catalog_readiness(request):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_food_catalog_readiness_vm()
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_readiness.html", base_vm.as_context())


@staff_member_required
@operation_not_found_as_404
def food_catalog_readiness_batch(request, batch_ref):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_readiness_batch_detail_vm(batch_ref)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_readiness_batch.html", base_vm.as_context())


@staff_member_required
@require_POST
def food_catalog_readiness_prepare(request):
    result, batch_ref = prepare_catalog_readiness_operation(
        actor=request.user,
        food_ids=request.POST.getlist("food_ids"),
        environment=request.POST.get("environment", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    if result.ok and batch_ref:
        return redirect("admin_operations_food_catalog_readiness_batch", batch_ref=batch_ref)
    return redirect("admin_operations_food_catalog_readiness")


@staff_member_required
@require_POST
@operation_not_found_as_404
def food_catalog_readiness_batch_action(request, batch_ref):
    result = perform_catalog_readiness_batch_operation(
        batch_ref=batch_ref,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_readiness_batch", batch_ref=batch_ref)


@staff_member_required
@require_POST
def food_catalog_source_portions_backfill(request):
    result = perform_source_portion_backfill_operation(
        actor=request.user,
        apply=request.POST.get("mode") == "apply",
        reason=request.POST.get("reason", ""),
        limit=request.POST.get("limit", 10),
        after_id=request.POST.get("after_id", 0),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_readiness")


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
@require_POST
def food_catalog_brand_dry_run(request):
    result = perform_brand_dry_run(
        actor=request.user,
        upload=request.FILES.get("file"),
        limit=request.POST.get("limit", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_brand_apply(request):
    result = perform_brand_apply(
        actor=request.user,
        upload=request.FILES.get("file"),
        limit=request.POST.get("limit", ""),
        dry_run_batch_id=request.POST.get("dry_run_batch_id", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_manual_dry_run(request):
    result = perform_manual_dry_run(actor=request.user, upload=request.FILES.get("file"), limit=request.POST.get("limit", ""), reason=request.POST.get("reason", ""))
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_manual_apply(request):
    result = perform_manual_apply(actor=request.user, upload=request.FILES.get("file"), limit=request.POST.get("limit", ""), dry_run_batch_id=request.POST.get("dry_run_batch_id", ""), reason=request.POST.get("reason", ""))
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_backfill_dry_run(request):
    result = perform_backfill_dry_run(actor=request.user, limit=request.POST.get("limit", ""), reason=request.POST.get("reason", ""))
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_backfill_apply(request):
    result = perform_backfill_apply(actor=request.user, limit=request.POST.get("limit", ""), dry_run_batch_id=request.POST.get("dry_run_batch_id", ""), reason=request.POST.get("reason", ""))
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@require_POST
def food_catalog_import_policy_action(request):
    result = perform_import_source_policy_operation(
        actor=request.user,
        source_type=request.POST.get("source_type", ""),
        source_name=request.POST.get("source_name", ""),
        max_batch_rows=request.POST.get("max_batch_rows", ""),
        action=request.POST.get("action", ""),
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_imports")


@staff_member_required
@operation_not_found_as_404
def food_catalog_candidate_detail(request, candidate_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_candidate_detail_vm(candidate_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_candidate_detail.html", base_vm.as_context())


@staff_member_required
@operation_not_found_as_404
def food_catalog_food_detail(request, catalog_food_id):
    ui_vm = build_ui_vm(ADMIN_OPERATIONS_OVERVIEW_VIEWMODE)
    content = build_catalog_food_detail_vm(catalog_food_id)
    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "admin_operations/food_catalog_food_detail.html", base_vm.as_context())


@staff_member_required
@require_POST
@operation_not_found_as_404
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
@operation_not_found_as_404
def food_catalog_food_action(request, catalog_food_id):
    result = perform_catalog_food_operation(
        catalog_food_id=catalog_food_id,
        action=request.POST.get("action", ""),
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_food", catalog_food_id=catalog_food_id)


@staff_member_required
@require_POST
def food_catalog_bulk_review(request):
    result = perform_catalog_food_bulk_review(
        actor=request.user,
        reason=request.POST.get("reason", ""),
        query=request.POST.get("q", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog")


@staff_member_required
@require_POST
@operation_not_found_as_404
def food_catalog_food_snapshot(request, catalog_food_id):
    result = perform_catalog_food_snapshot(
        catalog_food_id=catalog_food_id,
        actor=request.user,
        reason=request.POST.get("reason", ""),
    )
    flash_operation_result(request, result)
    return redirect("admin_operations_food_catalog_food", catalog_food_id=catalog_food_id)
