from urllib.parse import urlencode

from django.urls import reverse


SHARE_KIND_LABELS = {
    "dailyplan": "plan diario",
    "meal": "comida",
}


def build_share_invitation_email(
    *,
    request,
    share,
    kind: str,
    item_name: str,
    custom_subject: str | None = None,
    custom_message: str | None = None,
):
    sender_name = share.sender.username
    kind_label = SHARE_KIND_LABELS.get(kind, "elemento")
    accept_url_name = (
        "dailyplan_share_accept"
        if kind == "dailyplan"
        else "meal_share_accept"
    )

    clean_subject = (custom_subject or getattr(share, "subject", "") or item_name).strip()
    clean_message = (custom_message or getattr(share, "message", "") or "").strip()

    accept_path = reverse(accept_url_name, args=[share.token])
    accept_url = request.build_absolute_uri(accept_path)
    signup_url = request.build_absolute_uri(
        reverse("account_signup") + "?" + urlencode({"next": accept_path})
    )
    login_url = request.build_absolute_uri(
        reverse("account_login") + "?" + urlencode({"next": accept_path})
    )

    subject = clean_subject

    message_lines = [
        "Hola,",
        "",
        f"{sender_name} compartió este {kind_label} contigo en My Scoope:",
        item_name,
        "",
        "Asunto:",
        clean_subject,
        "",
    ]

    if clean_message:
        message_lines.extend([
            "Mensaje:",
            clean_message,
            "",
        ])

    message_lines.extend([
        "Para recibirlo en tu Inbox, abre este enlace:",
        accept_url,
        "",
        "Si todavía no tienes cuenta, puedes crearla aquí y volverás al enlace compartido:",
        signup_url,
        "",
        "Si ya tienes cuenta, puedes iniciar sesión aquí:",
        login_url,
        "",
        "Una vez aceptado, lo verás en Inbox y podrás guardarlo en Mi librería.",
        "",
        "My Scoope",
    ])

    return subject, "\n".join(message_lines)
