from notas.presentation.viewmodels.programs import build_program_metric_chart


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
                "page_icon": "calendar-range",
                "icon": "calendar-range",
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
