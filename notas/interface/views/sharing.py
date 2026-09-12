from __future__ import annotations

from urllib.parse import urlencode

from django.http import HttpResponse, HttpResponseNotModified
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.rate_limits import limit_sharing_claim, limit_sharing_preview
from notas.application.sharing.services import (
    ShareUnavailable,
    claim_share_resource,
    get_share_invitation_for_preview,
    get_share_resource_for_preview,
    record_share_preview,
)
from notas.domain.models import ShareClaim, ShareInvitation, ShareResource
from notas.presentation.sharing_cards import render_share_card_png, snapshot_card_etag

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
    card_url = request.build_absolute_uri(
        reverse(
            "share_invitation_card" if invitation is not None else "share_card",
            kwargs={"public_id": pending_id},
        )
    )
    canonical_url = request.build_absolute_uri(request.path)
    title = str(snapshot.get("subject", {}).get("title", "Contenido compartido"))
    subject_label = {
        ShareResource.SubjectType.DAILY_PLAN: "Plan diario",
        ShareResource.SubjectType.FOOD: "Alimento",
        ShareResource.SubjectType.MEAL: "Comida",
        ShareResource.SubjectType.PROGRAM: "Programa semanal",
    }.get(resource.subject_type, "Contenido")
    description = f"{title}: {subject_label.lower()} compartido con MyScoope."
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
            "card_url": card_url,
            "canonical_url": canonical_url,
            "share_description": description,
            "subject_label": subject_label,
        },
        status=status,
    )
    response["X-Robots-Tag"] = "noindex, nofollow"
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
@limit_sharing_preview
def share_preview(request, public_id):
    try:
        resource = get_share_resource_for_preview(public_id=public_id)
    except ShareUnavailable:
        return render(request, "notas/sharing/unavailable.html", status=404)
    record_share_preview(resource=resource)
    return _preview_response(request, resource)


@require_GET
@limit_sharing_preview
def share_invitation_preview(request, public_id):
    try:
        invitation = get_share_invitation_for_preview(public_id=public_id)
    except ShareUnavailable:
        return render(request, "notas/sharing/unavailable.html", status=404)
    record_share_preview(resource=invitation.resource)
    return _preview_response(request, invitation.resource, invitation=invitation)


def _card_response(request, resource: ShareResource):
    etag = f'"{snapshot_card_etag(resource.snapshot)}"'
    if request.headers.get("If-None-Match") == etag:
        response = HttpResponseNotModified()
    else:
        response = HttpResponse(
            render_share_card_png(resource.snapshot),
            content_type="image/png",
        )
    response["ETag"] = etag
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
@limit_sharing_preview
def share_card(request, public_id):
    try:
        resource = get_share_resource_for_preview(public_id=public_id)
    except ShareUnavailable:
        return HttpResponse(status=404)
    return _card_response(request, resource)


@require_GET
@limit_sharing_preview
def share_invitation_card(request, public_id):
    try:
        invitation = get_share_invitation_for_preview(public_id=public_id)
    except ShareUnavailable:
        return HttpResponse(status=404)
    return _card_response(request, invitation.resource)


@require_POST
@limit_sharing_claim
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
@limit_sharing_claim
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
