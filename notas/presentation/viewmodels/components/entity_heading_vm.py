from dataclasses import dataclass


@dataclass(frozen=True)
class EntitySubtitleVM:
    text: str
    icon: str | None = None
    modifier: str = ""
