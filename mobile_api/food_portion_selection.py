from __future__ import annotations

from dataclasses import dataclass
from math import isclose

from mobile_api.errors import MobileAPIError


@dataclass(frozen=True)
class PortionDisplaySelection:
    quantity: float
    measure: str


def normalize_portion_display_selection(
    *,
    food,
    metric_quantity,
    display_quantity=None,
    display_measure="",
) -> PortionDisplaySelection:
    metric_amount = float(metric_quantity or 0)
    if metric_amount <= 0:
        raise MobileAPIError("picker_quantity_invalid", "La porción debe ser mayor que cero.", 422)

    measure = str(display_measure or "").strip()
    if display_quantity is None and not measure:
        return PortionDisplaySelection(quantity=metric_amount, measure=food.portion_unit)
    if display_quantity is None or not measure:
        raise MobileAPIError(
            "picker_portion_display_invalid",
            "La cantidad y la medida seleccionadas deben enviarse juntas.",
            422,
        )

    selected_amount = float(display_quantity or 0)
    if selected_amount <= 0:
        raise MobileAPIError("picker_quantity_invalid", "La porción debe ser mayor que cero.", 422)

    if measure == food.portion_unit:
        expected_metric_amount = selected_amount
    else:
        household = (
            food.portions.filter(
                is_default=True,
                household_measure=measure,
                household_amount__isnull=False,
            )
            .only("grams", "household_amount")
            .first()
        )
        if household is None or float(household.household_amount or 0) <= 0:
            raise MobileAPIError(
                "picker_portion_measure_invalid",
                "La medida seleccionada no está disponible para este alimento.",
                422,
            )
        expected_metric_amount = selected_amount * float(household.grams) / float(household.household_amount)

    if not isclose(metric_amount, expected_metric_amount, rel_tol=0.001, abs_tol=0.01):
        raise MobileAPIError(
            "picker_portion_conversion_mismatch",
            "La equivalencia métrica de la porción no coincide con la medida seleccionada.",
            422,
        )
    return PortionDisplaySelection(quantity=selected_amount, measure=measure)
