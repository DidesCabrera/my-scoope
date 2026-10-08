from typing import Literal

from ninja import Field, Schema


class ListBulkDeleteInput(Schema):
    item_ids: list[int] = Field(min_length=1)


class ListActionResultData(Schema):
    affected_ids: list[int]
    skipped_ids: list[int]
    message: str


class ListActionResultEnvelope(Schema):
    ok: Literal[True] = True
    data: ListActionResultData
    error: None = None
