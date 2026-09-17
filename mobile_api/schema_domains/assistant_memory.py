from typing import Literal

from ninja import Schema


class AIClientMemoryCommitResultData(Schema):
    status: Literal["updated", "unchanged"]
    refresh_chat: bool = True


class AIClientMemoryCommitResultEnvelope(Schema):
    ok: Literal[True] = True
    data: AIClientMemoryCommitResultData
    error: None = None
