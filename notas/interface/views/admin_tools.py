import csv
from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from notas.application.services.access.capabilities import get_capabilities
from notas.domain.models import Food
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import (
    ADMIN_FOOD_CATALOG_VIEWMODE,
    ADMIN_HOME_VIEWMODE,
)
from notas.presentation.viewmodels.base_vm import BaseVM


@dataclass
class AdminCardVM:
    title: str
    description: str
    url: str
    icon: str


@dataclass
class AdminHomeContentVM:
    title: str
    subtitle: str
    cards: list[AdminCardVM]


@dataclass
class AdminFoodCatalogContentVM:
    title: str
    subtitle: str
    download_url: str
    template_url: str


def _user_is_admin(user):
    if not user or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    capabilities = get_capabilities(user)
    return bool(capabilities and capabilities.is_admin())


def admin_required(view_func):
    @login_required
    def wrapped(request, *args, **kwargs):
        if not _user_is_admin(request.user):
            messages.error(request, "No tienes permisos para acceder a Admin.")
            return redirect("home_view")
        return view_func(request, *args, **kwargs)
    return wrapped


def _format_csv_value(value):
    if value is None:
        return ""

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, float):
        return str(value).replace(".", ",")

    return value


@admin_required
def admin_home(request):
    ui_vm = build_ui_vm(ADMIN_HOME_VIEWMODE)

    content = AdminHomeContentVM(
        title="Admin Workspace",
        subtitle="Hub interno de Analytics, Operations y Knowledge.",
        cards=[
            AdminCardVM(
                title="Admin Analytics",
                description="Consulta métricas, señales de salud, actividad y alertas.",
                url="admin_analytics_overview",
                icon="chart-no-axes-combined",
            ),
            AdminCardVM(
                title="Admin Operations",
                description="Resuelve colas, catálogo, cuentas y acciones auditables.",
                url="admin_operations_overview",
                icon="wrench",
            ),
            AdminCardVM(
                title="Knowledge Center",
                description="Consulta orientación humana no normativa del sistema.",
                url="admin_knowledge_overview",
                icon="library-big",
            ),
            AdminCardVM(
                title="Foods Catalog",
                description="Acceso legacy para exportar y revisar cambios masivos.",
                url="admin_food_catalog",
                icon="database",
            ),
        ],
    )

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "notas/admin/home.html", base_vm.as_context())


@admin_required
def admin_foods_export_csv(request):
    field_names = []
    model_fields = []

    for field in Food._meta.concrete_fields:
        model_fields.append(field)
        if field.is_relation:
            field_names.append(field.attname)
        else:
            field_names.append(field.name)

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="foods_full_export.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow(field_names)

    queryset = Food.objects.all().order_by("id")

    for food in queryset:
        row = []
        for field in model_fields:
            attr_name = field.attname if field.is_relation else field.name
            value = getattr(food, attr_name)
            row.append(_format_csv_value(value))
        writer.writerow(row)

    return response


@admin_required
def admin_food_catalog(request):
    ui_vm = build_ui_vm(ADMIN_FOOD_CATALOG_VIEWMODE)

    if request.method == "POST":
        import pandas as pd

        upload = request.FILES.get("file")

        if not upload:
            messages.error(request, "Debes subir un archivo.")
            return redirect("admin_food_catalog")

        try:
            if upload.name.endswith(".csv"):
                df = pd.read_csv(upload, sep=";", decimal=",")
            elif upload.name.endswith(".xlsx"):
                df = pd.read_excel(upload)
            else:
                messages.error(request, "Formato no soportado. Usa .csv o .xlsx")
                return redirect("admin_food_catalog")

            required_columns = {"id", "name", "protein", "carbs", "fat"}
            missing = required_columns - set(df.columns)
            if missing:
                messages.error(
                    request,
                    f"Faltan columnas requeridas: {', '.join(sorted(missing))}"
                )
                return redirect("admin_food_catalog")

            updated = 0
            missing_ids = []
            invalid_rows = []

            for index, row in df.iterrows():
                food_id = row.get("id")

                if pd.isna(food_id):
                    invalid_rows.append(index + 2)
                    continue

                try:
                    food = Food.objects.get(pk=int(food_id))
                except Food.DoesNotExist:
                    missing_ids.append(int(food_id))
                    continue

                name = row.get("name")
                protein = row.get("protein")
                carbs = row.get("carbs")
                fat = row.get("fat")

                if pd.isna(name):
                    invalid_rows.append(index + 2)
                    continue

                try:
                    protein = float(protein) if not pd.isna(protein) else 0.0
                    carbs = float(carbs) if not pd.isna(carbs) else 0.0
                    fat = float(fat) if not pd.isna(fat) else 0.0
                except (TypeError, ValueError):
                    invalid_rows.append(index + 2)
                    continue

            food.name = str(name).strip()
            food.protein = protein
            food.carbs = carbs
            food.fat = fat

            update_fields = [
                "name",
                "protein",
                "carbs",
                "fat",
            ]

            if "is_global" in df.columns:
                raw_is_global = row.get("is_global")

                if not pd.isna(raw_is_global):
                    if isinstance(raw_is_global, str):
                        normalized_is_global = raw_is_global.strip().lower()
                        food.is_global = normalized_is_global in {
                            "1",
                            "true",
                            "t",
                            "yes",
                            "y",
                            "si",
                            "sí",
                        }
                    else:
                        food.is_global = bool(raw_is_global)

                    update_fields.append("is_global")

            food.save(update_fields=update_fields)
            updated += 1

            if missing_ids:
                messages.warning(
                    request,
                    f"IDs no encontrados: {', '.join(map(str, missing_ids[:20]))}"
                )

            if invalid_rows:
                messages.warning(
                    request,
                    f"Filas inválidas: {', '.join(map(str, invalid_rows[:20]))}"
                )

            messages.success(request, f"Foods actualizados: {updated}")
            return redirect("admin_food_catalog")

        except Exception as e:
            messages.error(request, f"Importación falló: {e}")
            return redirect("admin_food_catalog")

    content = AdminFoodCatalogContentVM(
        title="Foods Catalog",
        subtitle=(
            "Descarga el catálogo actual, edítalo en CSV/XLSX y vuelve a cargarlo "
            "para actualizar foods existentes por id."
        ),
        download_url="admin_foods_export_csv",
        template_url="admin_foods_template",
    )

    base_vm = BaseVM(ui=ui_vm, content=content)
    return render(request, "notas/admin/food_catalog.html", base_vm.as_context())


@admin_required
def admin_foods_template(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="foods_update_template.csv"'

    writer = csv.writer(response, delimiter=";")
    writer.writerow(["id", "name", "protein", "carbs", "fat", "is_global"])
    writer.writerow([1, "Chicken breast", "31,0", "0,0", "3,6", "true"])

    return response
