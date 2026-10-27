"""One in-app feed backed by the existing proposal and sharing read states."""

from allauth.account.models import EmailAddress
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from notas.domain.models import (
    InboxItem,
    NutritionProposal,
    ProductAnnouncement,
    ProductAnnouncementRead,
    ShareInvitation,
    ShareResource,
)


def _proposals(user):
    return NutritionProposal.objects.filter(
        Q(created_by=user) | Q(dailyplan__created_by=user),
        status=NutritionProposal.STATUS_PENDING_REVIEW,
    ).distinct()


def _shares(user):
    return InboxItem.objects.filter(owner=user, dismissed_at__isnull=True).select_related("resource", "resource__sender")


def _invitations(user):
    verified_emails = [email.casefold() for email in EmailAddress.objects.filter(user=user, verified=True).values_list("email", flat=True)]
    now = timezone.now()
    return ShareInvitation.objects.filter(
        recipient_email__in=verified_emails,
        status__in=[ShareInvitation.Status.PENDING, ShareInvitation.Status.DELIVERED],
        resource__status=ShareResource.Status.ACTIVE,
    ).filter(Q(resource__expires_at__isnull=True) | Q(resource__expires_at__gt=now)).exclude(
        resource__sender=user,
    ).select_related("resource", "resource__sender")


def _announcements():
    return ProductAnnouncement.objects.filter(is_active=True, published_at__lte=timezone.now())


def _share_visual_metadata(resource):
    if resource.subject_type != ShareResource.SubjectType.COMPARISON:
        return {"subject_type": resource.subject_type, "comparison_kind": None}
    summary = resource.snapshot.get("summary") or {}
    comparison = resource.snapshot.get("comparison") or {}
    comparison_kind = summary.get("comparison_kind") or comparison.get("kind")
    return {
        "subject_type": resource.subject_type,
        "comparison_kind": comparison_kind if comparison_kind in {"foods", "meals", "dailyplans"} else None,
    }


def unread_notification_count(user):
    if not user.is_authenticated:
        return 0
    return (
        _proposals(user).filter(is_read=False).count()
        + _shares(user).filter(read_at__isnull=True).count()
        + _invitations(user).filter(read_at__isnull=True).count()
        + _announcements().exclude(reads__user=user).count()
    )


def list_notifications(user, *, limit=50):
    if not user.is_authenticated:
        return []
    items = []
    for proposal in _proposals(user).order_by("-created_at", "-id")[:limit]:
        items.append({
            "kind": "proposal", "id": proposal.id, "title": proposal.title,
            "body": proposal.summary or "Tienes una propuesta pendiente de revisión.",
            "created_at": proposal.created_at, "is_read": proposal.is_read,
        })
    for share in _shares(user).order_by("-created_at", "-id")[:limit]:
        subject = (share.resource.snapshot.get("subject") or {})
        sender = share.resource.sender.get_full_name() or share.resource.sender.username
        items.append({
            "kind": "share", "id": share.id,
            **_share_visual_metadata(share.resource),
            "title": subject.get("title") or "Contenido compartido",
            "body": f"{sender} compartió este contenido contigo.",
            "created_at": share.created_at, "is_read": share.read_at is not None,
            "public_id": share.resource.public_id,
        })
    for invitation in _invitations(user).order_by("-created_at", "-id")[:limit]:
        resource = invitation.resource
        sender = resource.sender.get_full_name() or resource.sender.username
        subject = resource.snapshot.get("subject") or {}
        items.append({
            "kind": "invitation", "id": invitation.id,
            **_share_visual_metadata(resource),
            "title": invitation.subject or subject.get("title") or "Contenido compartido",
            "body": invitation.message or f"{sender} compartió este contenido contigo.",
            "created_at": invitation.created_at, "is_read": invitation.read_at is not None,
            "public_id": invitation.public_id,
        })
    announcements = list(_announcements().order_by("-published_at", "-id")[:limit])
    read_ids = set(ProductAnnouncementRead.objects.filter(
        user=user, announcement_id__in=[announcement.id for announcement in announcements],
    ).values_list("announcement_id", flat=True))
    for announcement in announcements:
        items.append({
            "kind": "announcement", "id": announcement.id,
            "title": announcement.title, "body": announcement.body,
            "created_at": announcement.published_at,
            "is_read": announcement.id in read_ids,
        })
    items.sort(key=lambda item: (item["created_at"], item["id"]), reverse=True)
    return items[:limit]


def mark_notification_read(user, kind, item_id):
    """Return whether the visible item belongs to the user and was updated."""
    if kind == "proposal":
        return bool(_proposals(user).filter(pk=item_id).update(is_read=True))
    if kind == "share":
        return bool(_shares(user).filter(pk=item_id).update(read_at=timezone.now()))
    if kind == "invitation":
        return bool(_invitations(user).filter(pk=item_id).update(read_at=timezone.now()))
    if kind == "announcement":
        announcement = _announcements().filter(pk=item_id).first()
        if announcement is None:
            return False
        ProductAnnouncementRead.objects.get_or_create(announcement=announcement, user=user)
        return True
    return False


@transaction.atomic
def mark_all_notifications_read(user):
    """Mark every currently visible notification for this user as read."""
    now = timezone.now()
    _proposals(user).filter(is_read=False).update(is_read=True)
    _shares(user).filter(read_at__isnull=True).update(read_at=now)
    _invitations(user).filter(read_at__isnull=True).update(read_at=now)
    read_ids = ProductAnnouncementRead.objects.filter(user=user).values("announcement_id")
    ProductAnnouncementRead.objects.bulk_create(
        [ProductAnnouncementRead(user=user, announcement=announcement, read_at=now)
         for announcement in _announcements().exclude(id__in=read_ids)],
        ignore_conflicts=True,
    )
