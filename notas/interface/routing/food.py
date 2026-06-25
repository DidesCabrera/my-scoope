"""Compatibility wrappers for older imports.

New presentation code should import these helpers from notas.presentation.routing.
"""

from notas.presentation.routing.food import food_list_url, food_url

__all__ = ["food_url", "food_list_url"]
