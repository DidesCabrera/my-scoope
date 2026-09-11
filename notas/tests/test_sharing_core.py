from datetime import timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notas.application.sharing.services import (
    ShareUnavailable,
    claim_share_resource,
    create_share_invitation,
    get_share_invitation_for_preview,
    mark_share_invitation_delivered,
    revoke_share_resource,
)
from notas.domain.models import InboxItem, ShareClaim, ShareInvitation, ShareResource

User = get_user_model()


class SharingCoreTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user(username="sender", email="sender@example.com")
        self.recipient = User.objects.create_user(username="recipient", email="recipient@example.com")
        self.resource = ShareResource.objects.create(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            source_object_id=7,
            snapshot={"name": "Plan"},
            snapshot_schema_version="sharing.snapshot.v1",
        )

    def test_link_claim_is_idempotent_and_creates_one_inbox_item(self):
        first_claim, first_item = claim_share_resource(
            resource=self.resource, user=self.recipient, source=ShareClaim.Source.LINK
        )
        second_claim, second_item = claim_share_resource(
            resource=self.resource, user=self.recipient, source=ShareClaim.Source.LINK
        )
        self.assertEqual(first_claim, second_claim)
        self.assertEqual(first_item, second_item)
        self.assertEqual(InboxItem.objects.count(), 1)

    def test_single_claim_policy_blocks_a_second_user(self):
        self.resource.claim_policy = ShareResource.ClaimPolicy.SINGLE
        self.resource.save(update_fields=["claim_policy"])
        claim_share_resource(resource=self.resource, user=self.recipient, source=ShareClaim.Source.LINK)
        other = User.objects.create_user(username="other", email="other@example.com")
        with self.assertRaisesMessage(ShareUnavailable, "share_resource_already_claimed"):
            claim_share_resource(resource=self.resource, user=other, source=ShareClaim.Source.LINK)

    def test_invitation_requires_matching_email(self):
        invitation = ShareInvitation.objects.create(
            resource=self.resource,
            recipient_email=self.recipient.email,
        )
        other = User.objects.create_user(username="other", email="other@example.com")
        with self.assertRaisesMessage(ShareUnavailable, "share_invitation_recipient_mismatch"):
            claim_share_resource(
                resource=self.resource,
                user=other,
                source=ShareClaim.Source.EMAIL,
                invitation=invitation,
            )

    def test_invitation_requires_a_verified_matching_email(self):
        invitation = ShareInvitation.objects.create(
            resource=self.resource,
            recipient_email=self.recipient.email,
        )
        with self.assertRaisesMessage(ShareUnavailable, "share_invitation_email_unverified"):
            claim_share_resource(
                resource=self.resource,
                user=self.recipient,
                source=ShareClaim.Source.EMAIL,
                invitation=invitation,
            )

        EmailAddress.objects.create(user=self.recipient, email=self.recipient.email, verified=True, primary=True)
        claim, _ = claim_share_resource(
            resource=self.resource,
            user=self.recipient,
            source=ShareClaim.Source.EMAIL,
            invitation=invitation,
        )
        self.assertEqual(claim.invitation, invitation)

    def test_expired_or_revoked_resource_cannot_be_claimed(self):
        self.resource.expires_at = timezone.now() - timedelta(seconds=1)
        self.resource.save(update_fields=["expires_at"])
        with self.assertRaisesMessage(ShareUnavailable, "share_resource_expired"):
            claim_share_resource(resource=self.resource, user=self.recipient, source=ShareClaim.Source.LINK)
        self.resource.refresh_from_db()
        self.assertEqual(self.resource.status, ShareResource.Status.ACTIVE)

        active = ShareResource.objects.create(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.DAILY_PLAN,
            snapshot={},
            snapshot_schema_version="sharing.snapshot.v1",
        )
        revoke_share_resource(resource=active, actor=self.sender)
        with self.assertRaisesMessage(ShareUnavailable, "share_resource_not_active"):
            claim_share_resource(resource=active, user=self.recipient, source=ShareClaim.Source.LINK)

    def test_only_sender_can_revoke(self):
        with self.assertRaisesMessage(ShareUnavailable, "share_resource_not_owned"):
            revoke_share_resource(resource=self.resource, actor=self.recipient)

    def test_claim_source_must_be_part_of_the_stable_contract(self):
        with self.assertRaisesMessage(ShareUnavailable, "share_claim_source_invalid"):
            claim_share_resource(resource=self.resource, user=self.recipient, source="unknown")

    def test_invitation_creation_is_owned_normalized_and_idempotent(self):
        first = create_share_invitation(
            resource=self.resource,
            sender=self.sender,
            recipient_email=" Recipient@Example.com ",
            subject=" Primer asunto ",
            message=" Hola ",
        )
        second = create_share_invitation(
            resource=self.resource,
            sender=self.sender,
            recipient_email="recipient@example.com",
            subject="Asunto actualizado",
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.recipient_email, "recipient@example.com")
        self.assertEqual(second.subject, "Asunto actualizado")
        self.assertEqual(ShareInvitation.objects.count(), 1)

    def test_invitation_preview_and_delivery_lifecycle(self):
        invitation = create_share_invitation(
            resource=self.resource,
            sender=self.sender,
            recipient_email=self.recipient.email,
        )
        self.assertEqual(
            get_share_invitation_for_preview(public_id=invitation.public_id),
            invitation,
        )
        mark_share_invitation_delivered(invitation=invitation)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ShareInvitation.Status.DELIVERED)
        self.assertIsNotNone(invitation.delivered_at)

    def test_claimed_invitation_cannot_be_reused_by_another_account(self):
        invitation = ShareInvitation.objects.create(
            resource=self.resource,
            recipient_email=self.recipient.email,
            recipient_user=self.recipient,
            status=ShareInvitation.Status.CLAIMED,
        )
        duplicate = User.objects.create_user(
            username="duplicate",
            email=self.recipient.email,
        )
        EmailAddress.objects.create(
            user=duplicate,
            email=duplicate.email,
            verified=True,
        )
        with self.assertRaisesMessage(ShareUnavailable, "share_invitation_already_claimed"):
            claim_share_resource(
                resource=self.resource,
                user=duplicate,
                source=ShareClaim.Source.EMAIL,
                invitation=invitation,
            )
