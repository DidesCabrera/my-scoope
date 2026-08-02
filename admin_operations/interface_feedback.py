"""HTTP feedback helpers for the Admin Operations interface layer."""

from django.contrib import messages

from admin_operations.services import AdminOperationResult


def flash_operation_result(request, result: AdminOperationResult) -> None:
    if result.ok:
        messages.success(request, result.message)
    else:
        messages.warning(request, result.message)
