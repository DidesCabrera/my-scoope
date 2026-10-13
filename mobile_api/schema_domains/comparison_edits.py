from typing import Literal

from ninja import Field, Schema


class SavedComparisonRenameInput(Schema):
    name: str = Field(min_length=1, max_length=255)


class SavedComparisonDeleteData(Schema):
    deleted_id: int


class SavedComparisonDeleteEnvelope(Schema):
    ok: Literal[True] = True
    data: SavedComparisonDeleteData
    error: None = None
