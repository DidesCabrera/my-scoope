"""Email channel adapter for normalized share invitations."""

from django.conf import settings

from email_delivery.services import deliver_share_invitation
from notas.application.services.notifications.share_emails import build_normalized_share_invitation_email
from notas.application.sharing.entities import get_or_create_entity_share_resource
from notas.application.sharing.services import create_share_invitation, mark_share_invitation_delivered


def deliver_normalized_entity_invitation(
    request,
    *,
    subject_type: str,
    subject_id: int,
    recipient_email: str,
    subject: str,
    message: str,
    variant: str = "",
):
    resource = get_or_create_entity_share_resource(
        sender=request.user,
        subject_type=subject_type,
        subject_id=subject_id,
        variant=variant,
    ).resource
    invitation = create_share_invitation(
        resource=resource,
        sender=request.user,
        recipient_email=recipient_email,
        subject=subject,
        message=message,
    )
    email_subject, email_message = build_normalized_share_invitation_email(
        request=request,
        invitation=invitation,
    )
    delivery = deliver_share_invitation(
        share=invitation,
        subject=email_subject,
        message=email_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
    )
    if delivery.sent:
        mark_share_invitation_delivered(invitation=invitation)
    return resource, invitation, delivery
