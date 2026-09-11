from urllib.parse import urlencode

from django.urls import reverse

SHARE_KIND_LABELS = {
    "dailyplan": "plan diario",
    "meal": "comida",
    "food": "alimento",
    "dpm": "comida de plan",
    "program": "programa semanal",
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
    accept_url_name = {
        "dailyplan": "dailyplan_share_accept",
        "meal": "meal_share_accept",
        "food": "food_share_accept",
        "dpm": "dailyplanmeal_share_accept",
        "program": "program_share_accept",
    }.get(kind)

    clean_subject = (custom_subject or getattr(share, "subject", "") or item_name).strip()
    clean_message = (custom_message or getattr(share, "message", "") or "").strip()

    accept_path = (
        reverse(accept_url_name, args=[share.token])
        if accept_url_name
        else reverse("inbox_list")
    )
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


def build_normalized_share_invitation_email(*, request, invitation):
    """Build transport content for the normalized invitation boundary."""
    snapshot = invitation.resource.snapshot
    item_name = snapshot.get("subject", {}).get("title", "Contenido compartido")
    sender_name = invitation.resource.sender.username
    preview_path = reverse(
        "share_invitation_preview",
        kwargs={"public_id": invitation.public_id},
    )
    preview_url = request.build_absolute_uri(preview_path)
    signup_url = request.build_absolute_uri(
        reverse("account_signup") + "?" + urlencode({"next": preview_path})
    )
    login_url = request.build_absolute_uri(
        reverse("account_login") + "?" + urlencode({"next": preview_path})
    )
    subject = invitation.subject.strip() or item_name
    message_lines = [
        "Hola,",
        "",
        f"{sender_name} compartió este plan diario contigo en MyScoope:",
        item_name,
        "",
    ]
    if invitation.message.strip():
        message_lines.extend(["Mensaje:", invitation.message.strip(), ""])
    message_lines.extend(
        [
            "Revisa la vista previa y confirma si quieres agregarlo a tu Inbox:",
            preview_url,
            "",
            "Si todavía no tienes cuenta, créala aquí y luego vuelve a la invitación:",
            signup_url,
            "",
            "Si ya tienes cuenta, inicia sesión aquí:",
            login_url,
            "",
            "Por seguridad, el correo verificado de tu cuenta debe coincidir con esta invitación.",
            "",
            "MyScoope",
        ]
    )
    return subject, "\n".join(message_lines)
