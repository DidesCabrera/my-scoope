from ninja import Field, Schema


class SavedComparisonRenameInput(Schema):
    name: str = Field(min_length=1, max_length=255)
