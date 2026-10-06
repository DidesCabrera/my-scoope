from typing import Literal

from ninja import Schema


class LearningSectionData(Schema):
    heading: str
    body: str


class LearningArticleData(Schema):
    slug: str
    title: str
    summary: str
    icon: str
    sections: list[LearningSectionData]
    takeaway: str
    source_label: str = ""
    source_url: str = ""


class LearningCatalogData(Schema):
    nutrition: list[LearningArticleData]
    manuals: list[LearningArticleData]


class LearningCatalogEnvelope(Schema):
    ok: Literal[True] = True
    data: LearningCatalogData
    error: None = None
