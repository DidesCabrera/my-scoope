from urllib.parse import urlencode

from django.template.loader import render_to_string
from django.urls import reverse

from email_delivery.branding import email_logo_url

SHARE_KIND_LABELS = {
    "dailyplan": "minuta diaria",
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
    subject_type = invitation.resource.subject_type
    is_plan_meal = snapshot.get("subject", {}).get("variant") == "daily_plan_meal"
    kind_label, title, eyebrow, button_color, eyebrow_color, button_text = {
        "daily_plan": ("plan diario", "Te compartieron un plan diario", "PLAN DIARIO COMPARTIDO", "#6229CE", "#C9AEFF", "#FFFFFF"),
        "food": ("alimento", "Te compartieron un alimento", "ALIMENTO COMPARTIDO", "#FF8800", "#FFB966", "#121212"),
        "meal": ("comida", "Te compartieron una comida", "COMIDA COMPARTIDA", "#CF34B0", "#F5A8E5", "#FFFFFF"),
        "program": ("programa semanal", "Te compartieron un programa", "PROGRAMA COMPARTIDO", "#1B6491", "#8CC7EB", "#FFFFFF"),
    }.get(
        subject_type,
        ("contenido", "Te compartieron contenido", "CONTENIDO COMPARTIDO", "#F5F5F5", "#B5B5B5", "#121212"),
    )
    if is_plan_meal:
        kind_label, title = "comida de plan", "Te compartieron una comida de plan"
    sender_name = invitation.resource.sender.username
    preview_path = reverse(
        "share_invitation_preview",
        kwargs={"public_id": invitation.public_id},
    )
    preview_url = request.build_absolute_uri(preview_path)
    subject = invitation.subject.strip() or item_name
    is_feminine = subject_type == "meal"
    article = "una" if is_feminine else "un"
    review = "Revísala" if is_feminine else "Revísalo"
    add = "la" if is_feminine else "lo"
    intro = (
        f"{sender_name} compartió {article} {kind_label} contigo en MyScoope. "
        f"{review} antes de decidir si {add} agregas a tu cuenta."
    )
    context = {
        "email_logo_url": email_logo_url(request),
        "email_eyebrow": eyebrow,
        "email_eyebrow_color": eyebrow_color,
        "email_title": title,
        "email_intro": intro,
        "email_item_label": kind_label.upper(),
        "email_item_title": item_name,
        "email_custom_message": invitation.message.strip(),
        "email_action_label": "Revisar invitación",
        "email_action_url": preview_url,
        "email_button_color": button_color,
        "email_button_text_color": button_text,
        "email_note": (
            f"Para aceptar{add}, inicia sesión o crea una cuenta con esta "
            "misma dirección de correo."
        ),
        "email_footer": "Recibiste este correo porque alguien compartió contenido contigo.",
    }
    return (
        subject,
        render_to_string("email_delivery/transactional.txt", context).strip(),
        render_to_string("email_delivery/transactional.html", context).strip(),
    )
