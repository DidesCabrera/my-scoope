"""HTTP feedback helpers for the Admin Operations interface layer."""

from functools import wraps

from django.contrib import messages
from django.http import Http404

from admin_operations.service_modules.common import AdminOperationResult, AdminOperationTargetNotFound


def operation_not_found_as_404(view_func):
    """Translate application lookup failures at the HTTP boundary."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        try:
            return view_func(*args, **kwargs)
        except AdminOperationTargetNotFound as exc:
            raise Http404(str(exc)) from exc

    return wrapped


def flash_operation_result(request, result: AdminOperationResult) -> None:
    if result.ok:
        messages.success(request, result.message)
    else:
        messages.warning(request, result.message)
