from dataclasses import dataclass
from typing import List, Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.services.personal_records import (
    update_body_record,
    update_planning_record,
    update_preference_record,
    update_weight_record,
)
from accounts.services.profile import build_account_credit_display
from notas.application.services.nutrition.body_metrics import get_basic_body_profile
from notas.domain.models import NutritionPreferenceProfile
from notas.interface.forms.forms import (
    PersonalPlanningForm,
    PersonalPreferencesForm,
    PersonalWeightForm,
    ProfileNutritionForm,
)
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import PERSONAL_RECORDS_VIEWMODE, PROFILE_VIEWMODE
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class ProfileFieldVM:
    label: str
    value: str
    hint: str = ""


@dataclass
class ProfileSectionVM:
    title: str
    eyebrow: str
    icon: str
    description: str
    fields: List[ProfileFieldVM]


@dataclass
class ProfileContentVM:
    title: str
    subtitle: str
    eyebrow: str
    icon: str
    active_section: str
    account_section: Optional[ProfileSectionVM]
    billing_section: Optional[ProfileSectionVM]
    nutrition_section: Optional[ProfileSectionVM]
    metrics_section: Optional[ProfileSectionVM]
    ai_context_section: Optional[ProfileSectionVM]
    weight_current: Optional[float]
    weight_updated_at: Optional[str]
    nutrition_form: ProfileNutritionForm


@dataclass
class PersonalRecordsContentVM:
    cards: List[dict]


@login_required
def profile_detail(request):
    return _render_profile_detail(request, active_section="account")


@login_required
def profile_nutrition(request):
    return _render_profile_detail(request, active_section="personal")


@login_required
def profile_credits(request):
    return _render_profile_detail(request, active_section="credits")


@login_required
def personal_records(request):
    """Present the user's persisted nutrition inputs as one visible hub."""
    profile = request.user.profile
    body_profile = get_basic_body_profile(request.user)
    weight_log = body_profile.current_weight_log
    preference_profile = NutritionPreferenceProfile.objects.filter(user=request.user).first()
    preferences = dict(preference_profile.preferences or {}) if preference_profile else {}

    cards = [
        {
            "key": "body",
            "eyebrow": "Base de cálculo",
            "title": "Ficha corporal",
            "icon": "id-card",
            "description": "Datos estables usados para estimar necesidades energéticas y nutricionales.",
            "fields": [
                ProfileFieldVM("Fecha de nacimiento", profile.birth_date.strftime("%Y-%m-%d") if profile.birth_date else "Sin completar"),
                ProfileFieldVM("Sexo nutricional", _format_sex(profile.sex)),
                ProfileFieldVM("Altura", f"{profile.height_cm} cm" if profile.height_cm else "Sin completar"),
            ],
            "action_href": reverse("personal_record_edit", kwargs={"section": "body"}),
            "action_label": "Editar información",
        },
        {
            "key": "planning",
            "eyebrow": "Planificación",
            "title": "Objetivo y actividad",
            "icon": "target",
            "description": "Contexto persistente que orienta objetivos, planes y programas.",
            "fields": [
                ProfileFieldVM("Objetivo nutricional", profile.get_nutrition_goal_display() if profile.nutrition_goal else "Sin completar"),
                ProfileFieldVM("Actividad habitual", profile.get_activity_level_display() if profile.activity_level else "Sin completar"),
                ProfileFieldVM("Entrenamientos", f"{profile.training_frequency} por semana" if profile.training_frequency is not None else "Sin completar"),
            ],
            "action_href": reverse("personal_record_edit", kwargs={"section": "planning"}),
            "action_label": "Editar información",
        },
        {
            "key": "preferences",
            "eyebrow": "Alimentación",
            "title": "Preferencias alimentarias",
            "icon": "salad",
            "description": "Patrón alimentario, alergias y alimentos evitados aprobados por ti.",
            "fields": [
                ProfileFieldVM("Patrón alimentario", _preference_label(preferences.get("dietary_pattern"))),
                ProfileFieldVM("Alergias o intolerancias", _list_label(preferences.get("allergies_or_intolerances"))),
                ProfileFieldVM("Alimentos evitados", _list_label(preferences.get("avoided_foods"))),
            ],
            "action_href": reverse("personal_record_edit", kwargs={"section": "preferences"}),
            "action_label": "Editar información",
        },
        {
            "key": "metrics",
            "eyebrow": "Seguimiento",
            "title": "Métricas corporales",
            "icon": "scale",
            "description": "Última medición disponible y su fecha, conservando el historial corporal.",
            "fields": [
                ProfileFieldVM("Peso actual", f"{body_profile.current_weight_kg:.1f} kg" if body_profile.current_weight_kg is not None else "Sin registro"),
                ProfileFieldVM("Última medición", weight_log.date.strftime("%Y-%m-%d") if weight_log else "Sin registro"),
                ProfileFieldVM("Origen", weight_log.get_source_display() if weight_log else "Sin registro"),
            ],
            "action_href": reverse("personal_record_edit", kwargs={"section": "metrics"}),
            "action_label": "Editar información",
        },
    ]
    vm = BaseVM(ui=build_ui_vm(PERSONAL_RECORDS_VIEWMODE), content=PersonalRecordsContentVM(cards=cards))
    return render(request, "notas/profile/personal_records.html", vm.as_context())


@login_required
def personal_record_edit(request, section):
    profile = request.user.profile
    stored = NutritionPreferenceProfile.objects.filter(user=request.user).first()
    preferences = dict(stored.preferences or {}) if stored else {}
    body_profile = get_basic_body_profile(request.user)
    definitions = {
        "body": {
            "title": "Editar ficha corporal", "icon": "id-card", "form_class": ProfileNutritionForm,
            "initial": {"birth_date": profile.birth_date, "sex": profile.sex, "height_cm": profile.height_cm},
            "save": lambda data: update_body_record(user=request.user, **data),
        },
        "planning": {
            "title": "Editar objetivo y actividad", "icon": "target", "form_class": PersonalPlanningForm,
            "initial": {"goal": profile.nutrition_goal, "activity_level": profile.activity_level, "training_frequency": profile.training_frequency},
            "save": lambda data: update_planning_record(user=request.user, **data),
        },
        "preferences": {
            "title": "Editar preferencias alimentarias", "icon": "salad", "form_class": PersonalPreferencesForm,
            "initial": {
                "dietary_pattern": preferences.get("dietary_pattern", ""),
                "allergies_or_intolerances": ", ".join(preferences.get("allergies_or_intolerances") or []),
                "avoided_foods": ", ".join(preferences.get("avoided_foods") or []),
            },
            "save": lambda data: update_preference_record(user=request.user, **data),
        },
        "metrics": {
            "title": "Registrar peso actual", "icon": "scale", "form_class": PersonalWeightForm,
            "initial": {"weight_kg": body_profile.current_weight_kg},
            "save": lambda data: update_weight_record(user=request.user, **data),
        },
    }
    definition = definitions.get(section)
    if definition is None:
        raise Http404
    form = definition["form_class"](request.POST or None, initial=definition["initial"])
    if request.method == "POST" and form.is_valid():
        definition["save"](form.cleaned_data)
        messages.success(request, "Información actualizada correctamente.")
        return redirect("personal_records")
    context = {
        "vm": BaseVM(ui=build_ui_vm(PERSONAL_RECORDS_VIEWMODE), content=None).as_context()["vm"],
        "record_form": form,
        "record_title": definition["title"],
        "record_icon": definition["icon"],
    }
    return render(request, "notas/profile/personal_record_edit.html", context)


@login_required
def profile_nutrition_update(request):
    if request.method != "POST":
        return redirect("profile_nutrition")

    profile = request.user.profile
    form = ProfileNutritionForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revisa los datos de tu ficha nutricional.")
        return _render_profile_detail(
            request,
            active_section="personal",
            nutrition_form=form,
        )

    profile.birth_date = form.cleaned_data["birth_date"]
    profile.sex = form.cleaned_data["sex"]
    profile.height_cm = form.cleaned_data["height_cm"]
    profile.save(update_fields=["birth_date", "sex", "height_cm"])
    messages.success(request, "Ficha nutricional actualizada correctamente.")
    return redirect("profile_nutrition")


def _render_profile_detail(request, *, active_section, nutrition_form=None):
    user = request.user
    profile = user.profile
    body_profile = get_basic_body_profile(user)
    last_weight_log = body_profile.current_weight_log
    current_weight = body_profile.current_weight_kg
    account_credits = build_account_credit_display(user)

    if nutrition_form is None:
        nutrition_form = ProfileNutritionForm(
            initial={
                "birth_date": profile.birth_date,
                "sex": profile.sex,
                "height_cm": profile.height_cm,
            }
        )

    account_section = ProfileSectionVM(
        eyebrow="Cuenta",
        title="Información de cuenta",
        icon="user-round",
        description="Datos principales de acceso, rol y plan asociado a tu cuenta.",
        fields=[
            ProfileFieldVM("Usuario", profile.user.username),
            ProfileFieldVM("Email", profile.user.email or "Sin email"),
            ProfileFieldVM("Rol", profile.get_role_display()),
            ProfileFieldVM("Miembro desde", profile.created_at.strftime("%Y-%m-%d")),
        ],
    )

    billing_section = ProfileSectionVM(
        eyebrow="Plan y créditos",
        title="Uso comercial",
        icon="wallet-cards",
        description=(
            "Resumen del plan comercial y los créditos visibles para AI Assistant. "
            "Los tokens y costos reales se mantienen como trazabilidad interna."
        ),
        fields=[
            ProfileFieldVM(
                "Plan comercial",
                account_credits.plan_name,
                f"Código {account_credits.plan_slug} · {account_credits.plan_source_label}",
            ),
            ProfileFieldVM(
                "Créditos disponibles",
                account_credits.available_label,
                f"{account_credits.credit_source_label} · periodo {account_credits.period}",
            ),
            ProfileFieldVM(
                "Créditos reservados",
                account_credits.reserved_label,
                "Reservas temporales para turnos AI en curso.",
            ),
            ProfileFieldVM(
                "Límite mensual",
                account_credits.monthly_limit_label,
                f"Incluye {account_credits.included_monthly_credits} créditos/mes.",
            ),
            ProfileFieldVM(
                "Límite diario",
                account_credits.daily_limit_label,
            ),
            ProfileFieldVM(
                "Estado suscripción",
                account_credits.subscription_status,
                account_credits.subscription_source,
            ),
        ],
    )

    nutrition_section = ProfileSectionVM(
        eyebrow="Ficha personal",
        title="Perfil nutricional",
        icon="id-card",
        description=(
            "Estos datos son la ficha personal base. My Scoope puede usarlos por defecto, "
            "pero el Assistant siempre puede calcular una propuesta con datos nuevos para otra persona."
        ),
        fields=[
            ProfileFieldVM(
                "Fecha de nacimiento",
                profile.birth_date.strftime("%Y-%m-%d") if profile.birth_date else "Sin completar",
            ),
            ProfileFieldVM(
                "Edad calculada",
                f"{body_profile.age_years} años" if body_profile.age_years is not None else "Sin completar",
                "Se recalcula dinámicamente desde la fecha de nacimiento.",
            ),
            ProfileFieldVM(
                "Sexo nutricional",
                _format_sex(profile.sex),
                "Dato usado por fórmulas de estimación energética.",
            ),
            ProfileFieldVM(
                "Altura",
                f"{profile.height_cm} cm" if profile.height_cm else "Sin completar",
            ),
        ],
    )

    metrics_section = ProfileSectionVM(
        eyebrow="Body Metrics",
        title="Métricas corporales",
        icon="scale",
        description=(
            "El peso se guarda como historial. Registrar un nuevo peso crea o actualiza "
            "la métrica del día sin borrar registros anteriores."
        ),
        fields=[
            ProfileFieldVM(
                "Peso actual",
                f"{current_weight:.1f} kg" if current_weight else "Sin registro",
            ),
            ProfileFieldVM(
                "Fecha último peso",
                last_weight_log.date.strftime("%Y-%m-%d") if last_weight_log else "Sin registro",
            ),
            ProfileFieldVM(
                "Origen último peso",
                last_weight_log.get_source_display() if last_weight_log else "Sin registro",
            ),
        ],
    )

    ai_context_section = ProfileSectionVM(
        eyebrow="AI / Solver",
        title="Contexto para propuestas",
        icon="sparkles",
        description=(
            "Actividad física y frecuencia de entrenamiento se completan en el primer chat "
            "nutricional o cuando una propuesta lo necesite."
        ),
        fields=[
            ProfileFieldVM("Actividad física", "Se preguntará en el chat"),
            ProfileFieldVM("Frecuencia de entrenamiento", "Se preguntará en el chat"),
            ProfileFieldVM("Preferencias default", "Contexto de sesión/propuesta", "Goal, comidas, complejidad y presupuesto no se persisten en v1."),
            ProfileFieldVM("Propuestas para terceros", "Permitidas", "El Assistant debe preguntar si usa tu ficha o datos nuevos."),
        ],
    )

    page_metadata = {
        "account": {
            "eyebrow": "Cuenta",
            "title": "Datos de cuenta",
            "subtitle": "Consulta la identidad y configuración general asociadas a tu acceso.",
            "icon": "user-round",
        },
        "personal": {
            "eyebrow": "Ficha personal",
            "title": "Perfil nutricional",
            "subtitle": "Mantén al día los datos corporales que My Scoope usa como referencia personal.",
            "icon": "id-card",
        },
        "credits": {
            "eyebrow": "Plan y créditos",
            "title": "Uso de créditos",
            "subtitle": "Revisa tu disponibilidad y los límites aplicados al uso de AI Assistant.",
            "icon": "wallet-cards",
        },
    }[active_section]

    content = ProfileContentVM(
        title=page_metadata["title"],
        subtitle=page_metadata["subtitle"],
        eyebrow=page_metadata["eyebrow"],
        icon=page_metadata["icon"],
        active_section=active_section,
        account_section=account_section if active_section == "account" else None,
        billing_section=billing_section if active_section == "credits" else None,
        nutrition_section=nutrition_section if active_section == "personal" else None,
        metrics_section=metrics_section if active_section == "personal" else None,
        ai_context_section=ai_context_section if active_section == "personal" else None,
        weight_current=current_weight,
        weight_updated_at=(
            last_weight_log.date.strftime("%Y-%m-%d")
            if last_weight_log else None
        ),
        nutrition_form=nutrition_form,
    )

    ui = build_ui_vm(PROFILE_VIEWMODE)

    vm = BaseVM(
        ui=ui,
        content=content,
    )

    context = vm.as_context()
    context["profile"] = profile

    return render(
        request,
        "notas/profile/detail.html",
        context,
    )


def _format_sex(sex: str) -> str:
    if sex == "female":
        return "Femenino"
    if sex == "male":
        return "Masculino"
    return "Sin completar"


def _list_label(value) -> str:
    values = [str(item).strip() for item in (value or []) if str(item).strip()]
    return ", ".join(values) if values else "Sin registrar"


def _preference_label(value) -> str:
    labels = {
        "omnivore": "Omnívoro",
        "vegetarian": "Vegetariano",
        "vegan": "Vegano",
        "pescatarian": "Pescetariano",
    }
    clean_value = str(value or "").strip()
    return labels.get(clean_value, clean_value.replace("_", " ").capitalize()) if clean_value else "Sin registrar"
