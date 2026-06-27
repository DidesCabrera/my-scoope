from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class BreadcrumbItem:
    label: str
    url: Optional[str] = None
    kind: str | None = None
    is_overflow: bool = False
    overflow_items: list["BreadcrumbItem"] = field(default_factory=list)


@dataclass
class UI:
    viewmode: str
    entity: str
    mode: str
    scope: Optional[str] = None
    nav_root: Optional[str] = None
    icon: str | None = None
    breadcrumb: list[BreadcrumbItem] = field(default_factory=list)
    section_label: Optional[str] = None
    title: Optional[str] = None
    root: Optional[str] = None
    page_icon: str | None = None
    is_inside: bool = False
    back_url: Optional[str] = None
    sidebar_sections: list[dict] = field(default_factory=list)


@dataclass
class BaseVM:
    ui: Any
    content: Optional[Any] = None

    def as_context(self):
        return {
            "vm": {
                "ui": asdict(self.ui),
                "content": asdict(self.content) if self.content else None,
            }
        }
