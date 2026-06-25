"""Compatibility wrappers for older imports.

New presentation code should import these helpers from notas.presentation.routing.
"""

from notas.presentation.routing.dailyplan import dailyplan_configure_url, dailyplan_url

__all__ = ["dailyplan_url", "dailyplan_configure_url"]
