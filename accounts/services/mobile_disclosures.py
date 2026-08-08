from django.utils import timezone

from notas.domain.models import Profile


def accept_current_mobile_disclosure(*, user) -> Profile:
    profile = user.profile
    profile.mobile_disclosure_version = Profile.MOBILE_DISCLOSURE_VERSION
    profile.mobile_disclosure_accepted_at = timezone.now()
    profile.save(update_fields=["mobile_disclosure_version", "mobile_disclosure_accepted_at"])
    return profile
