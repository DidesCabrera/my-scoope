from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class MyScoopeSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Keep Google OAuth signup/login as a one-step flow."""

    trusted_email_providers = {"google"}

    def _provider_id(self, provider):
        return getattr(provider, "id", provider)

    def is_email_verified(self, provider, email):
        if self._provider_id(provider) in self.trusted_email_providers:
            return True
        return super().is_email_verified(provider, email)

    def can_authenticate_by_email(self, login, email):
        provider = self._provider_id(login.account.provider)
        if provider in self.trusted_email_providers and email:
            return True
        return super().can_authenticate_by_email(login, email)
