from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class NutritionProposalListItemDTO:
    id: int
    dailyplan_id: int
    dailyplan_name: str
    created_by_id: int
    created_by_username: str
    reviewed_by_id: int | None
    reviewed_by_username: str | None
    status: str
    source: str
    title: str
    summary: str
    attachment_kind: str
    attachment_label: str
    attachment_name: str
    attachment_icon: str
    actions: list[dict]
    is_reviewable: bool
    is_final: bool
    created_at: str | None
    reviewed_at: str | None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class NutritionProposalDTO:
    id: int
    dailyplan_id: int
    dailyplan_name: str
    created_by_id: int
    created_by_username: str
    reviewed_by_id: int | None
    reviewed_by_username: str | None
    status: str
    source: str
    title: str
    summary: str
    targets: dict
    current_snapshot: dict
    proposed_payload: dict
    validation_summary: dict
    is_reviewable: bool
    is_final: bool
    created_at: str | None
    reviewed_at: str | None
    audit_events: list[dict]
    applied_at: str | None

    def as_dict(self) -> dict:
        return asdict(self)