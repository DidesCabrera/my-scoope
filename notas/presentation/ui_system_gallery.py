from notas.presentation.viewmodels.programs import build_program_metric_chart

ONBOARDING_STORYBOARD = (
    {"key": "login", "label": "Acceso", "eyebrow": "Acceso", "title": "Inicia sesión para guardar tu progreso", "description": "Usa tu cuenta para continuar el proceso en cualquiera de tus dispositivos.", "icon": "log-in"},
    {"key": "value", "label": "Funciones principales", "eyebrow": "Funciones principales", "title": "Qué puedes hacer con My Scoope", "description": "My Scoope organiza tu objetivo, calcula referencias nutricionales y las convierte en un plan diario que puedes revisar.", "icon": "target"},
    {"key": "structure", "label": "Organización nutricional", "eyebrow": "Estructura del sistema", "title": "Cómo se organiza tu alimentación", "description": "La información se organiza en cuatro niveles reutilizables: alimentos, comidas, planes diarios y programas.", "icon": "layers-3"},
    {"key": "panels", "label": "Lectura de paneles", "eyebrow": "Paneles de información", "title": "Cómo leer los paneles", "description": "Cada panel muestra primero un resumen y permite consultar calorías, macronutrientes y detalle.", "icon": "eye"},
    {"key": "control", "label": "Asistencia y decisiones", "eyebrow": "Asistencia y control", "title": "Cómo funciona la asistencia", "description": "La asistencia interpreta tu solicitud y prepara una propuesta. Tú la revisas antes de aplicarla.", "icon": "brain-circuit"},
    {"key": "progress", "label": "Seguimiento del progreso", "eyebrow": "Seguimiento", "title": "Cómo revisar tu progreso", "description": "Compara lo planificado con tus registros para decidir si necesitas ajustar el plan.", "icon": "chart-no-axes-column-increasing"},
    {"key": "disclosures", "label": "Información y límites", "eyebrow": "Uso responsable", "title": "Información importante antes de continuar", "description": "Revisa qué hace My Scoope, qué no hace y qué decisiones quedan bajo tu responsabilidad.", "icon": "shield-check"},
    {"key": "goal", "label": "Objetivo nutricional", "eyebrow": "Objetivo nutricional", "title": "Define tu objetivo", "description": "Tu objetivo orienta el ajuste energético y la referencia inicial de proteína.", "icon": "target"},
    {"key": "identity", "label": "Datos personales", "eyebrow": "Datos para el cálculo", "title": "Ingresa tus datos personales", "description": "La edad y el sexo usado para el cálculo forman parte de la estimación de tu gasto basal.", "icon": "circle-user-round"},
    {"key": "measurements", "label": "Medidas corporales", "eyebrow": "Datos para el cálculo", "title": "Ingresa tus medidas actuales", "description": "La altura y el peso permiten estimar tu gasto energético y calcular referencias por kilogramo.", "icon": "scale"},
    {"key": "activity", "label": "Actividad y entrenamiento", "eyebrow": "Datos para el cálculo", "title": "Describe tu actividad y entrenamiento", "description": "Separa el movimiento habitual de los entrenamientos para evitar contarlos dos veces.", "icon": "dumbbell"},
    {"key": "summary", "label": "Resumen de la ficha", "eyebrow": "Resumen de la ficha", "title": "Revisa tu información", "description": "Comprueba los datos y la estimación inicial antes de continuar.", "icon": "gauge"},
    {"key": "plans", "label": "Planes disponibles", "eyebrow": "Planes disponibles", "title": "Elige un plan", "description": "Compara lo que incluyen Free, Basic y Pro. Puedes cambiar de plan más adelante.", "icon": "badge-dollar-sign"},
    {"key": "home", "label": "Primer plan diario", "eyebrow": "Siguiente paso", "title": "Tu ficha está lista", "description": "Ahora puedes crear un plan diario a partir de tu objetivo y tus datos.", "icon": "house"},
)


def _program_week(week_number, calories):
    day_labels = ["L", "M", "M", "J", "V", "S", "D"]
    days = []
    for day_number, day_label in enumerate(day_labels, start=1):
        total_kcal = calories + ((day_number % 3) - 1) * 90
        protein = 145 + day_number * 2
        carbs = 220 + day_number * 4
        fat = 58 + day_number
        days.append(
            {
                "day_number": day_number,
                "day_label": day_label,
                "program_day": True,
                "dailyplan": {"name": f"Plan {day_label} · Semana {week_number}"},
                "snapshot": {
                    "total_kcal": total_kcal,
                    "protein": protein,
                    "carbs": carbs,
                    "fat": fat,
                    "kcal_protein": protein * 4,
                    "kcal_carbs": carbs * 4,
                    "kcal_fat": fat * 9,
                    "alloc": {"protein": 30, "carbs": 44, "fat": 26},
                },
            }
        )
    return {"week_number": week_number, "days": days}


def build_ui_system_gallery_examples():
    weeks = [_program_week(1, 2140), _program_week(2, 2260)]
    program_chart = build_program_metric_chart(weeks, current_weight=78)
    return {
        "onboarding_storyboard": ONBOARDING_STORYBOARD,
        "kpis": {
            "tot_kcal": 2140,
            "ppk": 1.8,
            "g_protein": 155,
            "g_carbs": 238,
            "g_fat": 62,
            "alloc_protein": 30,
            "alloc_carbs": 44,
            "alloc_fat": 26,
            "kcal_protein": 620,
            "kcal_carbs": 952,
            "kcal_fat": 558,
        },
        "list_header_vm": {
            "ui": {
                "entity": "program",
                "scope": "personal",
                "section_label": "Mis librerias",
                "page_icon": "bookmark",
                "icon": "calendar",
                "title": "Programas",
            },
            "content": {"item_count": 3},
        },
        "program_kpis": {"start_date": "17 ago", "end_date": "27 sep", "elapsed_days": 24, "remaining_days": 18, "total_days": 42, "progress": 57, "adhered_days": 82, "planned_adherence_days": 87, "adherence": 97},
        "program_card": {
            "child_id": 1,
            "title": "Programa de recomposición",
            "weeks_count": 2,
            "filled_days_count": 14,
            "foods_count": 36,
            "chart": program_chart,
            "metadata": {"owner": "Tú"},
            "actions": [
                {
                    "key": "detail",
                    "label": "Ver programa",
                    "url": "#program-card",
                    "method": "get",
                    "icon": "chevron-right",
                    "desktop_position": "inline",
                    "mobile_position": "inline",
                    "extra_class": "",
                }
            ],
        },
    }
