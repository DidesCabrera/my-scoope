from urllib.parse import parse_qs, urlsplit

from allauth.account.adapter import DefaultAccountAdapter
from allauth.core import context as allauth_context
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse

from email_delivery.branding import email_logo_url
from email_delivery.models import EmailDeliveryAttempt
from email_delivery.services import deliver_account_message


class MyScoopeAccountAdapter(DefaultAccountAdapter):
    def get_email_confirmation_url(self, request, emailconfirmation):
        url = super().get_email_confirmation_url(request, emailconfirmation)
        if request is None:
            return url

        next_url = request.POST.get("next") or request.GET.get("next", "")
        destination = urlsplit(next_url)
        parameters = parse_qs(destination.query)
        is_mobile_signup = (
            not destination.scheme
            and not destination.netloc
            and destination.path == reverse("oauth_authorize")
            and parameters.get("client_id") == ["myscoope-ios"]
            and parameters.get("redirect_uri") == ["myscoope://oauth/callback"]
        )
        if not is_mobile_signup:
            return url

        return request.build_absolute_uri(
            reverse("mobile_confirm_email", kwargs={"key": emailconfirmation.key})
        )

    def send_mail(self, template_prefix: str, email: str, context: dict) -> None:
        request = allauth_context.request
        ctx = {
            "request": request,
            "email": email,
            "current_site": get_current_site(request),
        }
        ctx.update(context)
        ctx["email_logo_url"] = email_logo_url(request)
        if "email_confirmation" in template_prefix:
            ctx.update(
                email_eyebrow="SEGURIDAD DE TU CUENTA",
                email_title="Confirma tu correo electrónico",
                email_intro=(
                    "Para terminar de crear tu cuenta en MyScoope, confirma que "
                    "esta dirección de correo es tuya."
                ),
                email_action_label="Confirmar mi correo",
                email_action_url=ctx.get("activate_url", ""),
                email_note="Si no creaste una cuenta, puedes ignorar este mensaje.",
                email_footer="Mensaje de seguridad de tu cuenta · Ayuda y soporte",
            )
        elif "password_reset_key" in template_prefix:
            ctx.update(
                email_eyebrow="SEGURIDAD DE TU CUENTA",
                email_title="Crea una nueva contraseña",
                email_intro=(
                    "Recibimos una solicitud para cambiar la contraseña de tu "
                    "cuenta de MyScoope."
                ),
                email_action_label="Crear nueva contraseña",
                email_action_url=ctx["password_reset_url"],
                email_note=(
                    "Si no pediste este cambio, puedes ignorar este mensaje. "
                    "Tu contraseña actual seguirá funcionando."
                ),
                email_footer="Mensaje relacionado con tu cuenta · Ayuda y soporte",
            )
        elif "account_already_exists" in template_prefix:
            ctx.update(
                email_eyebrow="ACCESO A TU CUENTA",
                email_title="Ya tienes una cuenta en MyScoope",
                email_intro=(
                    "Recibimos un intento de registro con esta dirección de "
                    "correo. Ya existe una cuenta asociada a ella."
                ),
                email_action_label="Recuperar mi contraseña",
                email_action_url=ctx["password_reset_url"],
                email_note=(
                    "Si recuerdas tu contraseña, puedes iniciar sesión "
                    "normalmente. Si no hiciste este intento, puedes ignorar "
                    "el mensaje."
                ),
                email_footer="Mensaje relacionado con tu cuenta · Ayuda y soporte",
            )
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
