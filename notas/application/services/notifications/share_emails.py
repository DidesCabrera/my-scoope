from urllib.parse import urlencode

from django.urls import reverse


SHARE_KIND_LABELS = {
    "dailyplan": "plan diario",
    "meal": "comida",
}


def build_share_invitation_email(*, request, share, kind: str, item_name: str):
    sender_name = share.sender.username
    kind_label = SHARE_KIND_LABELS.get(kind, "elemento")
    accept_url_name = (
        "dailyplan_share_accept"
        if kind == "dailyplan"
        else "meal_share_accept"
    )

    accept_path = reverse(accept_url_name, args=[share.token])
    accept_url = request.build_absolute_uri(accept_path)
    signup_url = request.build_absolute_uri(
        reverse("account_signup") + "?" + urlencode({"next": accept_path})
    )
    login_url = request.build_absolute_uri(
        reverse("account_login") + "?" + urlencode({"next": accept_path})
    )

    subject = f"{sender_name} compartió un {kind_label} contigo en My Scoope"
    message = (
        f"Hola,\n\n"
        f"{sender_name} compartió este {kind_label} contigo en My Scoope:\n"
        f"{item_name}\n\n"
        f"Para recibirlo en tu Inbox, abre este enlace:\n"
        f"{accept_url}\n\n"
        f"Si todavía no tienes cuenta, puedes crearla aquí y volverás al enlace compartido:\n"
        f"{signup_url}\n\n"
        f"Si ya tienes cuenta, puedes iniciar sesión aquí:\n"
        f"{login_url}\n\n"
        f"Una vez aceptado, lo verás en Compartir / Inbox y podrás guardarlo en Mi librería.\n\n"
        f"My Scoope"
    )

    return subject, message
