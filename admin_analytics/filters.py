from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar, Mapping

from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.utils import timezone


@dataclass(frozen=True)
class AdminAnalyticsFilterOption:
    value: str
    label: str
    is_active: bool = False


@dataclass(frozen=True)
class AdminAnalyticsFilters:
    period: str = "7d"
    user_segment: str = "all"

    PERIOD_DAYS: ClassVar[dict[str, int]] = {
        "7d": 7,
        "30d": 30,
        "90d": 90,
    }
    PERIOD_LABELS: ClassVar[dict[str, str]] = {
        "7d": "Últimos 7 días",
        "30d": "Últimos 30 días",
        "90d": "Últimos 90 días",
    }
    USER_SEGMENT_LABELS: ClassVar[dict[str, str]] = {
        "all": "Todos los usuarios",
        "staff": "Staff",
        "members": "Miembros",
    }

    @classmethod
    def from_querydict(cls, params: Mapping[str, str] | None = None) -> "AdminAnalyticsFilters":
        params = params or {}
        period = params.get("period", "7d")
        user_segment = params.get("user_segment", "all")
        if period not in cls.PERIOD_DAYS:
            period = "7d"
        if user_segment not in cls.USER_SEGMENT_LABELS:
            user_segment = "all"
        return cls(period=period, user_segment=user_segment)

    @property
    def days(self) -> int:
        return self.PERIOD_DAYS[self.period]

    @property
    def period_label(self) -> str:
        return self.PERIOD_LABELS[self.period]

    @property
    def user_segment_label(self) -> str:
        return self.USER_SEGMENT_LABELS[self.user_segment]

    @property
    def summary_label(self) -> str:
        return f"{self.period_label} · {self.user_segment_label}"

    def since(self, *, now=None):
        now = now or timezone.now()
        return now - timedelta(days=self.days)

    @property
    def period_options(self) -> list[AdminAnalyticsFilterOption]:
        return [
            AdminAnalyticsFilterOption(value=value, label=label, is_active=value == self.period)
            for value, label in self.PERIOD_LABELS.items()
        ]

    @property
    def user_segment_options(self) -> list[AdminAnalyticsFilterOption]:
        return [
            AdminAnalyticsFilterOption(value=value, label=label, is_active=value == self.user_segment)
            for value, label in self.USER_SEGMENT_LABELS.items()
        ]


    def as_template_context(self) -> dict:
        return {
            "period": self.period,
            "user_segment": self.user_segment,
            "period_label": self.period_label,
            "user_segment_label": self.user_segment_label,
            "summary_label": self.summary_label,
            "period_options": self.period_options,
            "user_segment_options": self.user_segment_options,
        }

    def apply_user_segment(self, queryset: QuerySet, field_name: str = "user") -> QuerySet:
        if self.user_segment == "all":
            return queryset
        lookup = f"{field_name}__is_staff"
        return queryset.filter(**{lookup: self.user_segment == "staff"})

    def user_queryset(self):
        User = get_user_model()
        users = User.objects.all()
        if self.user_segment == "staff":
            return users.filter(is_staff=True)
        if self.user_segment == "members":
            return users.filter(is_staff=False)
        return users
