from ninja import Field, Schema


class AIChatRenameInput(Schema):
    name: str = Field(min_length=1, max_length=140)
