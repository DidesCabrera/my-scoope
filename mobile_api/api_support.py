from __future__ import annotations

from typing import Any

from mobile_api.errors import MobileAPIError


def success(data: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def require_scope(auth: Any, scope: str) -> None:
    if scope not in auth.token.scopes:
        raise MobileAPIError(
            code="mobile_scope_missing",
            message="The access token does not include the required mobile scope.",
            status_code=403,
            details={"required_scope": scope},
        )


def form_error(form: Any, *, code: str, message: str) -> MobileAPIError:
    return MobileAPIError(
        code=code,
        message=message,
        status_code=422,
        details={"fields": form.errors.get_json_data()},
    )


def calendarization_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    not_found = {
        "calendarization_not_found",
        "calendarized_day_not_found",
        "calendarization_revision_not_found",
        "calendarization_review_not_found",
        "calendarization_program_not_owned",
    }
    conflicts = {
        "calendarization_idempotency_conflict",
        "calendarization_revision_already_decided",
        "calendarization_revision_no_longer_eligible",
        "calendarization_incomplete_confirmation_required",
        "calendarization_replacement_confirmation_required",
        "calendarization_current_conflict",
        "calendarization_cannot_pause",
        "calendarization_cannot_resume",
        "calendarization_cannot_cancel",
    }
    return MobileAPIError(
        code=code,
        message="The lived-program operation could not be completed.",
        status_code=404 if code in not_found else 409 if code in conflicts else 422,
    )


def food_label_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    return MobileAPIError(
        code=code,
        message="The confirmed nutrition label could not be saved.",
        status_code=409 if code == "food_label_idempotency_conflict" else 422,
    )


def proposal_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    not_found = {
        "proposal_not_found",
        "proposal_review_not_allowed",
        "proposal_cancel_not_allowed",
    }
    conflicts = {
        "proposal_is_not_pending_review",
        "proposal_is_not_applicable",
        "proposal_apply_requires_applicable_status",
        "proposal_already_applied",
        "proposal_is_final",
        "proposal_external_subject_ack_required",
        "proposal_apply_not_supported",
    }
    return MobileAPIError(
        code=code,
        message="No pudimos completar la operación de la propuesta.",
        status_code=404 if code in not_found else 409 if code in conflicts else 422,
    )


def comparison_error(exc: ValueError) -> MobileAPIError:
    code = str(exc)
    not_found = {"comparison_item_not_available", "saved_comparison_not_found"}
    conflicts = {"saved_comparison_kind_mismatch"}
    return MobileAPIError(
        code=code,
        message="No pudimos completar la comparación.",
        status_code=404 if code in not_found else 409 if code in conflicts else 422,
    )
