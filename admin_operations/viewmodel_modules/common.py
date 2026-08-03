from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdminOperationsMetricVM:
    label: str
    value: str
    helper: str = ""
    icon: str = "activity"




__all__ = ['AdminOperationsMetricVM']
