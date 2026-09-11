"""Lifecycle services for portable share resources."""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from notas.domain.models import InboxItem, ShareClaim, ShareInvitation, ShareResource


class ShareUnavailable(ValueError):
    pass


def _active_resource(resource: ShareResource, *, now=None) -> ShareResource:
    current_time = now or timezone.now()
    if resource.status != ShareResource.Status.ACTIVE:
        raise ShareUnavailable("share_resource_not_active")
    if resource.expires_at and resource.expires_at <= current_time:
        raise ShareUnavailable("share_resource_expired")
    return resource


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
        if (user.email or "").strip().casefold() != invitation.recipient_email.strip().casefold():
            raise ShareUnavailable("share_invitation_recipient_mismatch")
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
