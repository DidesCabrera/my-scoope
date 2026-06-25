"""Compatibility wrappers for older imports.

New presentation code should import these helpers from notas.presentation.routing.
"""

from notas.presentation.routing.meal import meal_configure_url, meal_list_url, meal_url

__all__ = ["meal_url", "meal_configure_url", "meal_list_url"]
