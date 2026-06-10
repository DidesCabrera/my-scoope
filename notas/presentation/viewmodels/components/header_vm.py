from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HeaderActionVM:
    key: str
    label: str
    url: str
    method: str = "get"
    icon: Optional[str] = None
    is_back: bool = False
    order: int = 0
    desktop_position: str = "inline"
    mobile_position: str = "inline"
    disabled: bool = False
    extra_class: str = ""


@dataclass
class HeaderVM:
    title: str = ""
    actions: list[HeaderActionVM] = field(default_factory=list)
    desktop_inline_actions: list[HeaderActionVM] = field(default_factory=list)
    desktop_menu_actions: list[HeaderActionVM] = field(default_factory=list)
    mobile_inline_actions: list[HeaderActionVM] = field(default_factory=list)
    mobile_menu_actions: list[HeaderActionVM] = field(default_factory=list)