from django.test import SimpleTestCase

from notas.application.sharing.contracts import (
    SHARE_SNAPSHOT_SCHEMA_VERSION,
    ShareClaimPolicy,
    ShareClaimSource,
    ShareInvitationStatus,
    ShareResourceStatus,
    ShareSubjectType,
    ShareVisibility,
)


class SharingContractTests(SimpleTestCase):
    def test_public_vocabulary_is_stable_and_channel_independent(self):
        self.assertEqual(SHARE_SNAPSHOT_SCHEMA_VERSION, "sharing.snapshot.v1")
        self.assertEqual(set(ShareSubjectType), {
            ShareSubjectType.DAILY_PLAN, ShareSubjectType.FOOD,
            ShareSubjectType.MEAL, ShareSubjectType.PROGRAM,
        })
        self.assertEqual(set(ShareClaimPolicy), {
            ShareClaimPolicy.NONE, ShareClaimPolicy.SINGLE, ShareClaimPolicy.MULTIPLE,
        })
        self.assertEqual(set(ShareResourceStatus), {
            ShareResourceStatus.ACTIVE, ShareResourceStatus.REVOKED, ShareResourceStatus.EXPIRED,
        })
        self.assertEqual(set(ShareInvitationStatus), {
            ShareInvitationStatus.PENDING, ShareInvitationStatus.DELIVERED,
            ShareInvitationStatus.CLAIMED, ShareInvitationStatus.REVOKED,
            ShareInvitationStatus.EXPIRED,
        })
        self.assertEqual(set(ShareClaimSource), {ShareClaimSource.EMAIL, ShareClaimSource.LINK})
        self.assertEqual(set(ShareVisibility), {ShareVisibility.UNLISTED})
