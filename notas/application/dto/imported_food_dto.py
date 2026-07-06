"""Compatibility import for Food Catalog import contracts.

Import DTO ownership moved to ``food_catalog.application.imports``. This module
keeps the historical notas import path stable while import commands are migrated
incrementally.
"""

from food_catalog.application.imports.contracts import ImportedFoodDTO

__all__ = ["ImportedFoodDTO"]
