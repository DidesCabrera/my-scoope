"""Lifecycle services for portable share resources."""

from __future__ import annotations

from allauth.account.models import EmailAddress
from django.db import transaction
from django.utils import timezone

from notas.domain.models import InboxItem, ShareClaim, ShareInvitation, ShareResource


class ShareUnavailable(ValueError):
    pass


def _normalized_email(value: str) -> str:
    return (value or "").strip().casefold()


def _active_resource(resource: ShareResource, *, now=None) -> ShareResource:
    current_time = now or timezone.now()
    if resource.status != ShareResource.Status.ACTIVE:
        raise ShareUnavailable("share_resource_not_active")
    if resource.expires_at and resource.expires_at <= current_time:
        raise ShareUnavailable("share_resource_expired")
    return resource


def get_share_resource_for_preview(*, public_id, now=None) -> ShareResource:
    resource = ShareResource.objects.filter(public_id=public_id).first()
    if resource is None:
        raise ShareUnavailable("share_resource_not_found")
    return _active_resource(resource, now=now)


def get_share_invitation_for_preview(*, public_id, now=None) -> ShareInvitation:
    invitation = ShareInvitation.objects.select_related("resource").filter(public_id=public_id).first()
    if invitation is None:
        raise ShareUnavailable("share_invitation_not_found")
    _active_resource(invitation.resource, now=now)
    if invitation.status in {ShareInvitation.Status.REVOKED, ShareInvitation.Status.EXPIRED}:
        raise ShareUnavailable("share_invitation_not_active")
    return invitation


@transaction.atomic
def create_share_invitation(
    *, resource: ShareResource, sender, recipient_email: str, subject: str = "", message: str = ""
) -> ShareInvitation:
    locked = ShareResource.objects.select_for_update().get(pk=resource.pk)
    _active_resource(locked)
    if locked.sender_id != sender.id:
        raise ShareUnavailable("share_resource_not_owned")
    normalized_email = _normalized_email(recipient_email)
    if not normalized_email:
        raise ShareUnavailable("share_invitation_recipient_required")
    invitation, _ = ShareInvitation.objects.get_or_create(
        resource=locked,
        recipient_email=normalized_email,
        defaults={"subject": subject.strip(), "message": message.strip()},
    )
    updates = []
    clean_subject = subject.strip()
    clean_message = message.strip()
    if invitation.subject != clean_subject:
        invitation.subject = clean_subject
        updates.append("subject")
    if invitation.message != clean_message:
        invitation.message = clean_message
        updates.append("message")
    if updates:
        invitation.save(update_fields=[*updates, "updated_at"])
    return invitation


def mark_share_invitation_delivered(*, invitation: ShareInvitation, now=None) -> ShareInvitation:
    if invitation.status == ShareInvitation.Status.PENDING:
        invitation.status = ShareInvitation.Status.DELIVERED
        invitation.delivered_at = now or timezone.now()
        invitation.save(update_fields=["status", "delivered_at", "updated_at"])
    return invitation


@transaction.atomic
def revoke_share_resource(*, resource: ShareResource, actor, now=None) -> ShareResource:
    locked = ShareResource.objects.select_for_update().get(pk=resource.pk)
    if locked.sender_id != actor.id:
        raise ShareUnavailable("share_resource_not_owned")
    if locked.status == ShareResource.Status.REVOKED:
        return locked
    locked.status = ShareResource.Status.REVOKED
    locked.revoked_at = now or timezone.now()
    locked.save(update_fields=["status", "revoked_at", "updated_at"])
    locked.invitations.exclude(status=ShareInvitation.Status.CLAIMED).update(status=ShareInvitation.Status.REVOKED)
    return locked


@transaction.atomic
def claim_share_resource(
    *,
    resource: ShareResource,
    user,
    source: str,
    invitation: ShareInvitation | None = None,
    now=None,
) -> tuple[ShareClaim, InboxItem]:
    if source not in ShareClaim.Source.values:
        raise ShareUnavailable("share_claim_source_invalid")
    locked = ShareResource.objects.select_for_update().get(pk=resource.pk)
    _active_resource(locked, now=now)
    existing = ShareClaim.objects.filter(resource=locked, user=user).first()
    if existing is not None:
        return existing, InboxItem.objects.get(claim=existing)
    if locked.claim_policy == ShareResource.ClaimPolicy.NONE:
        raise ShareUnavailable("share_claims_disabled")
    if locked.claim_policy == ShareResource.ClaimPolicy.SINGLE and locked.claims.exists():
        raise ShareUnavailable("share_resource_already_claimed")
    if invitation is not None:
        invitation = ShareInvitation.objects.select_for_update().get(pk=invitation.pk, resource=locked)
        if invitation.status in {ShareInvitation.Status.REVOKED, ShareInvitation.Status.EXPIRED}:
            raise ShareUnavailable("share_invitation_not_active")
        if (
            invitation.status == ShareInvitation.Status.CLAIMED
            and invitation.recipient_user_id != user.id
        ):
            raise ShareUnavailable("share_invitation_already_claimed")
        if (user.email or "").strip().casefold() != invitation.recipient_email.strip().casefold():
            raise ShareUnavailable("share_invitation_recipient_mismatch")
        if not EmailAddress.objects.filter(
            user=user,
            email__iexact=invitation.recipient_email,
            verified=True,
        ).exists():
            raise ShareUnavailable("share_invitation_email_unverified")
    claim = ShareClaim.objects.create(
        resource=locked,
        user=user,
        invitation=invitation,
        source=source,
    )
    inbox_item = InboxItem.objects.create(owner=user, resource=locked, claim=claim)
    if invitation is not None:
        invitation.recipient_user = user
        invitation.status = ShareInvitation.Status.CLAIMED
        invitation.claimed_at = now or timezone.now()
        invitation.save(update_fields=["recipient_user", "status", "claimed_at", "updated_at"])
    return claim, inbox_item
