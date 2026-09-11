from __future__ import annotations

from urllib.parse import urlencode

from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from notas.application.sharing.services import (
    ShareUnavailable,
    claim_share_resource,
    get_share_invitation_for_preview,
    get_share_resource_for_preview,
)
from notas.domain.models import ShareClaim, ShareInvitation, ShareResource

PENDING_SHARE_CLAIM_SESSION_KEY = "pending_share_claim_public_id"
PENDING_SHARE_INVITATION_SESSION_KEY = "pending_share_invitation_public_id"


def _preview_response(
    request,
    resource: ShareResource,
    *,
    invitation: ShareInvitation | None = None,
    error_code: str = "",
    status: int = 200,
):
    snapshot = resource.snapshot
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("subject"), dict):
        return render(request, "notas/sharing/unavailable.html", status=404)
    already_claimed = bool(
        request.user.is_authenticated
        and resource.claims.filter(user=request.user).exists()
    )
    session_key = (
        PENDING_SHARE_INVITATION_SESSION_KEY
        if invitation is not None
        else PENDING_SHARE_CLAIM_SESSION_KEY
    )
    pending_id = invitation.public_id if invitation is not None else resource.public_id
    pending_claim = (
        request.user.is_authenticated
        and request.session.get(session_key) == str(pending_id)
        and request.GET.get("claim") == "continue"
    )
    claim_url = reverse(
        "share_invitation_claim" if invitation is not None else "share_claim",
        kwargs={"public_id": pending_id},
    )
    response = render(
        request,
        "notas/sharing/preview.html",
        {
            "resource": resource,
            "snapshot": snapshot,
            "already_claimed": already_claimed,
            "pending_claim": pending_claim,
            "claim_error": error_code,
            "claim_url": claim_url,
            "invitation": invitation,
        },
        status=status,
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
def share_preview(request, public_id):
    try:
        resource = get_share_resource_for_preview(public_id=public_id)
    except ShareUnavailable:
        return render(request, "notas/sharing/unavailable.html", status=404)
    return _preview_response(request, resource)


@require_GET
def share_invitation_preview(request, public_id):
    try:
        invitation = get_share_invitation_for_preview(public_id=public_id)
    except ShareUnavailable:
        return render(request, "notas/sharing/unavailable.html", status=404)
    return _preview_response(request, invitation.resource, invitation=invitation)


@require_POST
def share_claim(request, public_id):
    try:
        resource = get_share_resource_for_preview(public_id=public_id)
    except ShareUnavailable:
        return render(request, "notas/sharing/unavailable.html", status=404)

    if not request.user.is_authenticated:
        request.session[PENDING_SHARE_CLAIM_SESSION_KEY] = str(resource.public_id)
        continuation = reverse("share_preview", kwargs={"public_id": resource.public_id}) + "?claim=continue"
        login_url = reverse("account_login") + "?" + urlencode({"next": continuation})
        return redirect(login_url)

    try:
        claim_share_resource(resource=resource, user=request.user, source=ShareClaim.Source.LINK)
    except ShareUnavailable as exc:
        if str(exc) in {"share_resource_not_active", "share_resource_expired"}:
            return render(request, "notas/sharing/unavailable.html", status=404)
        return _preview_response(request, resource, error_code=str(exc), status=409)

    request.session.pop(PENDING_SHARE_CLAIM_SESSION_KEY, None)
    return redirect(reverse("share_preview", kwargs={"public_id": resource.public_id}) + "?claimed=1")


@require_POST
def share_invitation_claim(request, public_id):
    try:
        invitation = get_share_invitation_for_preview(public_id=public_id)
    except ShareUnavailable:
        return render(request, "notas/sharing/unavailable.html", status=404)

    if not request.user.is_authenticated:
        request.session[PENDING_SHARE_INVITATION_SESSION_KEY] = str(invitation.public_id)
        continuation = (
            reverse("share_invitation_preview", kwargs={"public_id": invitation.public_id})
            + "?claim=continue"
        )
        login_url = reverse("account_login") + "?" + urlencode({"next": continuation})
        return redirect(login_url)

    try:
        claim_share_resource(
            resource=invitation.resource,
            user=request.user,
            source=ShareClaim.Source.EMAIL,
            invitation=invitation,
        )
    except ShareUnavailable as exc:
        if str(exc) in {
            "share_resource_not_active",
            "share_resource_expired",
            "share_invitation_not_active",
        }:
            return render(request, "notas/sharing/unavailable.html", status=404)
        return _preview_response(
            request,
            invitation.resource,
            invitation=invitation,
            error_code=str(exc),
            status=409,
        )

    request.session.pop(PENDING_SHARE_INVITATION_SESSION_KEY, None)
    return redirect(
        reverse("share_invitation_preview", kwargs={"public_id": invitation.public_id})
        + "?claimed=1"
    )
