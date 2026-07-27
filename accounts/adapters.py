from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_context
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.sites.shortcuts import get_current_site

from email_delivery.models import EmailDeliveryAttempt
from email_delivery.services import deliver_account_message


class MyScoopeAccountAdapter(DefaultAccountAdapter):
    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        request = allauth_context.request
        ctx = {
            "request": request,
            "email": email,
            "current_site": get_current_site(request),
        }
        ctx.update(context)
        message = self.render_mail(template_prefix, email, ctx)
        category = EmailDeliveryAttempt.CATEGORY_ACCOUNT
        if "email_confirmation" in template_prefix:
            category = EmailDeliveryAttempt.CATEGORY_EMAIL_VERIFICATION
        elif "password_reset" in template_prefix:
            category = EmailDeliveryAttempt.CATEGORY_PASSWORD_RESET
        deliver_account_message(
            category=category,
            recipient_email=email,
            message=message,
            actor=context.get("user"),
        )


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
