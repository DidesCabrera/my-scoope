from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from notas.application.sharing.services import ShareUnavailable, claim_share_resource, revoke_share_resource
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
