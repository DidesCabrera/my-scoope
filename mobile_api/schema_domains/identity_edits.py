from ninja import Field, Schema


class UsernameRenameInput(Schema):
    username: str = Field(min_length=1, max_length=150)
