from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from notas.application.services.nutrition.weight import record_weight


@login_required
def register_weight(request):
    back_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/app/profile/"

    if request.method != "POST":
        return redirect(back_url)

    try:
        weight = float(request.POST.get("weight", 0))
    except (TypeError, ValueError):
        messages.error(request, "Ingresa un número válido.")
        return redirect(back_url)

    if weight <= 0:
        messages.error(request, "El peso debe ser mayor a 0.")
        return redirect(back_url)

    record_weight(request.user, weight)

    messages.success(request, "Peso registrado correctamente.")
    return redirect(back_url)