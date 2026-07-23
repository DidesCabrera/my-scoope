from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from django.conf import settings
from django.urls import reverse

from admin_knowledge.policy import KNOWLEDGE_DOCUMENT_PATHS, POLICY


_COLLECTIONS = (
    {
        "key": "human_guides",
        "label": "Guías para personas",
        "description": (
            "Orientación explicativa curada manualmente. No define contratos "
            "ni reemplaza el código o la documentación normativa."
        ),
        "icon": "book-open-check",
    },
)
_COLLECTION = _COLLECTIONS[0]
_ALLOWED_DOCUMENT_PATHS = frozenset(KNOWLEDGE_DOCUMENT_PATHS)
_TABLE_SEPARATOR = re.compile(r"^:?-{3,}:?$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_UNORDERED_ITEM = re.compile(r"^\s*[-*]\s+(.+)$")
_ORDERED_ITEM = re.compile(r"^\s*\d+[.)]\s+(.+)$")


@dataclass(frozen=True)
class KnowledgeDocument:
    relative_path: str
    title: str
    status: str
    date: str
    audience: str
    excerpt: str
    collection_key: str
    collection_label: str
    source: str
    absolute_path: Path

    @property
    def url(self) -> str:
        return reverse(
            "admin_knowledge_document",
            kwargs={"document_path": self.relative_path},
        )


def _docs_root() -> Path:
    return (Path(settings.BASE_DIR) / "docs").resolve()


def _collection_for(relative_path: PurePosixPath) -> dict[str, str] | None:
    if relative_path.as_posix() not in _ALLOWED_DOCUMENT_PATHS:
        return None
    return _COLLECTION


def _resolve_document_path(document_path: str) -> Path:
    relative_path = PurePosixPath(str(document_path or "").strip())
    if (
        not relative_path.parts
        or relative_path.is_absolute()
        or relative_path.suffix.lower() != ".md"
        or any(part in {"", ".", ".."} for part in relative_path.parts)
        or _collection_for(relative_path) is None
    ):
        raise FileNotFoundError("knowledge_document_not_available")

    docs_root = _docs_root()
    candidate = (docs_root / Path(*relative_path.parts)).resolve()
    if not candidate.is_relative_to(docs_root) or not candidate.is_file():
        raise FileNotFoundError("knowledge_document_not_available")
    return candidate


def _metadata_value(lines: list[str], key: str) -> str:
    pattern = re.compile(rf"^(?:-\s*)?{re.escape(key)}:\s*(.+)$", re.IGNORECASE)
    for line in lines[:30]:
        match = pattern.match(line.strip())
        if match:
            return match.group(1).strip()
    return ""


def _extract_excerpt(lines: list[str]) -> str:
    paragraph: list[str] = []
    in_fence = False
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line:
            if paragraph:
                break
            continue
        if (
            line.startswith("#")
            or line.startswith("|")
            or line.startswith(("- ", "* ", "> "))
            or re.match(
                r"^(Status|Estado|Date|Fecha|Audience|Audiencia|Role|Authority|Update-Policy):",
                line,
                re.IGNORECASE,
            )
        ):
            continue
        paragraph.append(line)
        if len(" ".join(paragraph)) >= 220:
            break
    excerpt = " ".join(paragraph)
    if len(excerpt) > 240:
        return f"{excerpt[:237].rstrip()}…"
    return excerpt or "Documento operativo de My Scoope."


def _build_document(path: Path) -> KnowledgeDocument:
    docs_root = _docs_root()
    relative_path = PurePosixPath(path.relative_to(docs_root).as_posix())
    collection = _collection_for(relative_path)
    if collection is None:
        raise FileNotFoundError("knowledge_document_not_available")

    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    title = next(
        (match.group(2).strip() for line in lines if (match := _HEADING.match(line))),
        path.stem.replace("_", " ").replace("-", " ").title(),
    )
    return KnowledgeDocument(
        relative_path=relative_path.as_posix(),
        title=title,
        status=_metadata_value(lines, "Status") or _metadata_value(lines, "Estado") or "documented",
        date=_metadata_value(lines, "Date") or _metadata_value(lines, "Fecha"),
        audience=_metadata_value(lines, "Audience") or _metadata_value(lines, "Audiencia"),
        excerpt=_extract_excerpt(lines),
        collection_key=collection["key"],
        collection_label=collection["label"],
        source=source,
        absolute_path=path,
    )


def discover_documents() -> tuple[KnowledgeDocument, ...]:
    docs_root = _docs_root()
    return tuple(
        _build_document(docs_root / relative_path)
        for relative_path in KNOWLEDGE_DOCUMENT_PATHS
    )


def load_document(document_path: str) -> KnowledgeDocument:
    return _build_document(_resolve_document_path(document_path))


def _searchable(value: str) -> str:
    return " ".join(str(value or "").casefold().split())


def build_knowledge_index(query: str = "") -> dict[str, object]:
    documents = discover_documents()
    normalized_query = _searchable(query)
    featured = list(documents)
    featured.sort(
        key=lambda document: (
            document.relative_path.endswith("/README.md"),
            document.date,
            document.title,
        ),
        reverse=True,
    )

    search_results: list[KnowledgeDocument] = []
    if normalized_query:
        search_results = [
            document
            for document in documents
            if normalized_query
            in _searchable(
                " ".join(
                    (
                        document.title,
                        document.status,
                        document.audience,
                        document.excerpt,
                        document.source,
                    )
                )
            )
        ]
        search_results.sort(key=lambda document: (document.date, document.title), reverse=True)

    collections = []
    for definition in _COLLECTIONS:
        matching = [
            document
            for document in documents
            if document.collection_key == definition["key"]
        ]
        matching.sort(key=lambda document: (document.date, document.title), reverse=True)
        collections.append(
            {
                **definition,
                "count": len(matching),
                "documents": matching[:8],
            }
        )

    return {
        "title": "Knowledge Center",
        "subtitle": (
            "Orientación explicativa para personas. No define cómo funciona "
            "el sistema ni reemplaza sus fuentes normativas."
        ),
        "query": query.strip(),
        "total": len(documents),
        "featured": featured,
        "collections": collections,
        "search_results": search_results,
        "policy": POLICY,
    }


def build_document_detail(document_path: str) -> dict[str, object]:
    document = load_document(document_path)
    related = [
        candidate
        for candidate in discover_documents()
        if candidate.collection_key == document.collection_key
        and candidate.relative_path != document.relative_path
    ]
    related.sort(key=lambda candidate: (candidate.date, candidate.title), reverse=True)
    return {
        "document": document,
        "html": render_markdown(document),
        "related": related[:6],
        "policy": POLICY,
    }


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(_TABLE_SEPARATOR.match(cell) for cell in cells)


def _is_block_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    if (
        not line.strip()
        or line.startswith("```")
        or _HEADING.match(line)
        or _UNORDERED_ITEM.match(line)
        or _ORDERED_ITEM.match(line)
        or line.lstrip().startswith(">")
    ):
        return True
    return (
        index + 1 < len(lines)
        and "|" in line
        and _is_table_separator(lines[index + 1])
    )


def _safe_link_target(href: str, document: KnowledgeDocument) -> tuple[str, bool]:
    href = href.strip()
    parsed = urlsplit(href)
    if parsed.scheme in {"http", "https", "mailto"}:
        return href, parsed.scheme in {"http", "https"}
    if parsed.scheme or parsed.netloc:
        return "#", False
    if href.startswith("#"):
        return href, False

    path_part, marker, fragment = href.partition("#")
    if not path_part.lower().endswith(".md"):
        return "#", False
    candidate = (document.absolute_path.parent / path_part).resolve()
    docs_root = _docs_root()
    if not candidate.is_relative_to(docs_root) or not candidate.is_file():
        return "#", False
    relative = candidate.relative_to(docs_root).as_posix()
    if relative not in _ALLOWED_DOCUMENT_PATHS:
        return "#", False
    target = reverse(
        "admin_knowledge_document",
        kwargs={"document_path": relative},
    )
    if marker and fragment:
        target = f"{target}#{fragment}"
    return target, False


def _render_inline(text: str, document: KnowledgeDocument, *, links: bool = True) -> str:
    tokens: dict[str, str] = {}

    def store(value: str) -> str:
        key = f"\x00TOKEN{len(tokens)}\x00"
        tokens[key] = value
        return key

    text = re.sub(
        r"`([^`]+)`",
        lambda match: store(f"<code>{escape(match.group(1))}</code>"),
        text,
    )

    if links:
        def replace_link(match: re.Match[str]) -> str:
            label = _render_inline(match.group(1), document, links=False)
            target, external = _safe_link_target(match.group(2), document)
            external_attributes = ' target="_blank" rel="noopener noreferrer"' if external else ""
            return store(
                f'<a href="{escape(target, quote=True)}"{external_attributes}>{label}</a>'
            )

        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, text)

    rendered = escape(text)
    rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
    rendered = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", rendered)
    for key, value in tokens.items():
        rendered = rendered.replace(escape(key), value)
    return rendered


def render_markdown(document: KnowledgeDocument) -> str:
    lines = document.source.splitlines()
    rendered: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if line.startswith("```"):
            language = re.sub(r"[^a-zA-Z0-9_-]", "", line[3:].strip())
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1 if index < len(lines) else 0
            language_attribute = f' data-language="{escape(language)}"' if language else ""
            rendered.append(
                f"<pre{language_attribute}><code>{escape(chr(10).join(code_lines))}</code></pre>"
            )
            continue

        heading_match = _HEADING.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            anchor = re.sub(r"[^a-z0-9]+", "-", heading_text.casefold()).strip("-")
            rendered.append(
                f'<h{level} id="{escape(anchor, quote=True)}">'
                f"{_render_inline(heading_text, document)}</h{level}>"
            )
            index += 1
            continue

        if index + 1 < len(lines) and "|" in line and _is_table_separator(lines[index + 1]):
            headers = _split_table_row(line)
            index += 2
            rows: list[list[str]] = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append(_split_table_row(lines[index]))
                index += 1
            header_html = "".join(
                f"<th>{_render_inline(cell, document)}</th>" for cell in headers
            )
            body_html = "".join(
                "<tr>"
                + "".join(
                    f"<td>{_render_inline(cell, document)}</td>"
                    for cell in row
                )
                + "</tr>"
                for row in rows
            )
            rendered.append(
                '<div class="admin-knowledge-table-wrap"><table>'
                f"<thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody>"
                "</table></div>"
            )
            continue

        unordered_match = _UNORDERED_ITEM.match(line)
        if unordered_match:
            items = []
            while index < len(lines) and (match := _UNORDERED_ITEM.match(lines[index])):
                items.append(f"<li>{_render_inline(match.group(1), document)}</li>")
                index += 1
            rendered.append(f"<ul>{''.join(items)}</ul>")
            continue

        ordered_match = _ORDERED_ITEM.match(line)
        if ordered_match:
            items = []
            while index < len(lines) and (match := _ORDERED_ITEM.match(lines[index])):
                items.append(f"<li>{_render_inline(match.group(1), document)}</li>")
                index += 1
            rendered.append(f"<ol>{''.join(items)}</ol>")
            continue

        if line.lstrip().startswith(">"):
            quotes = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quotes.append(lines[index].lstrip()[1:].strip())
                index += 1
            rendered.append(
                f"<blockquote>{_render_inline(' '.join(quotes), document)}</blockquote>"
            )
            continue

        paragraph = [stripped]
        index += 1
        while index < len(lines) and not _is_block_start(lines, index):
            paragraph.append(lines[index].strip())
            index += 1
        rendered.append(f"<p>{_render_inline(' '.join(paragraph), document)}</p>")

    return "\n".join(rendered)
