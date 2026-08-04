from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

VALID_STATUS_CLASSES = {
    "accepted", "active", "completed", "current", "draft", "paused", "planned", "superseded"
}


@dataclass(frozen=True)
class DocumentEntry:
    path: str
    kind: str
    identifier: str
    title: str
    status: str
    status_class: str
    domain: str

    def as_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "kind": self.kind,
            "identifier": self.identifier,
            "title": self.title,
            "status": self.status,
            "status_class": self.status_class,
            "domain": self.domain,
        }


@dataclass(frozen=True)
class RegistryFinding:
    code: str
    severity: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True)
class DocumentRegistry:
    entries: tuple[DocumentEntry, ...]
    findings: tuple[RegistryFinding, ...]

    @property
    def valid(self) -> bool:
        return not any(finding.severity == "error" for finding in self.findings)

    def as_dict(self) -> dict[str, object]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            key = f"{entry.kind}:{entry.status_class}"
            counts[key] = counts.get(key, 0) + 1
        return {
            "contract": "myscoope.document_registry.v1",
            "valid": self.valid,
            "counts": counts,
            "entries": [entry.as_dict() for entry in self.entries],
            "findings": [finding.as_dict() for finding in self.findings],
        }


def build_document_registry(root: Path) -> DocumentRegistry:
    docs_root = root / "docs"
    paths = sorted((docs_root / "10_active_cycles").glob("*.md")) + sorted(
        (docs_root / "20_decisions").glob("*.md")
    )
    entries = []
    findings = []
    for path in paths:
        if path.name == "README.md":
            continue
        entry, entry_findings = _parse_document(root, path)
        entries.append(entry)
        findings.extend(entry_findings)

    decision_ids: dict[str, list[DocumentEntry]] = {}
    for entry in entries:
        if entry.kind == "decision" and entry.identifier:
            decision_ids.setdefault(entry.identifier, []).append(entry)
    for identifier, matching in decision_ids.items():
        if len(matching) > 1:
            for entry in matching:
                findings.append(RegistryFinding(
                    code="decision.duplicate_identifier",
                    severity="error",
                    path=entry.path,
                    message=f"Decision identifier {identifier} is used by {len(matching)} documents.",
                ))
    return DocumentRegistry(entries=tuple(entries), findings=tuple(findings))


def _parse_document(root: Path, path: Path) -> tuple[DocumentEntry, list[RegistryFinding]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((line[2:].strip() for line in lines if line.startswith("# ")), "")
    kind = "decision" if path.parent.name == "20_decisions" else "cycle"
    filename_identifier = _filename_identifier(path.name, kind)
    title_identifier = _title_identifier(title, kind)
    identifier = title_identifier or filename_identifier
    raw_status = _extract_status(lines)
    status_class = _normalize_status(raw_status)
    relative_path = str(path.relative_to(root))
    findings = []

    if not title:
        findings.append(RegistryFinding("document.missing_title", "error", relative_path, "Missing H1 title."))
    if not raw_status:
        findings.append(RegistryFinding("document.missing_status", "error", relative_path, "Missing document status."))
    elif status_class not in VALID_STATUS_CLASSES:
        findings.append(RegistryFinding(
            "document.unknown_status", "error", relative_path, f"Unrecognized status: {raw_status}"
        ))
    if kind == "decision" and filename_identifier != title_identifier:
        findings.append(RegistryFinding(
            "decision.identifier_mismatch",
            "error",
            relative_path,
            f"Filename identifier {filename_identifier or 'missing'} does not match title {title_identifier or 'missing'}.",
        ))

    return DocumentEntry(
        path=relative_path,
        kind=kind,
        identifier=identifier,
        title=title,
        status=raw_status,
        status_class=status_class,
        domain=_infer_domain(path.name),
    ), findings


def _extract_status(lines: list[str]) -> str:
    for index, line in enumerate(lines[:20]):
        inline = re.match(r"^(?:-\s*)?Status:\s*(.+)$", line.strip(), flags=re.IGNORECASE)
        if inline:
            return inline.group(1).strip()
        if line.strip().lower() in {"## status", "## estado"}:
            for candidate in lines[index + 1:index + 5]:
                if candidate.strip() and not candidate.startswith("#"):
                    return candidate.strip().rstrip(".")
    return ""


def _normalize_status(status: str) -> str:
    normalized = status.lower().strip()
    if any(word in normalized for word in ("accepted", "aceptad")):
        return "accepted"
    if "superseded" in normalized:
        return "superseded"
    if "draft" in normalized:
        return "draft"
    if "paused" in normalized:
        return "paused"
    if "planned" in normalized:
        return "planned"
    if "current" in normalized:
        return "current"
    if any(word in normalized for word in ("completed", "complete", "implemented")):
        return "completed"
    if "active" in normalized:
        return "active"
    return "unknown"


def _filename_identifier(name: str, kind: str) -> str:
    pattern = r"^(\d{4})-" if kind == "decision" else r"^([A-Za-z]+\d{2})"
    match = re.match(pattern, name)
    return match.group(1).upper() if match else ""


def _title_identifier(title: str, kind: str) -> str:
    pattern = r"^(?:Decision\s+)?(\d{4})\b" if kind == "decision" else r"^([A-Za-z]+\d{2})"
    match = re.match(pattern, title, flags=re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _infer_domain(filename: str) -> str:
    domain_tokens = (
        ("food", "food_catalog"), ("nutrition-solver", "nutrition_solver"),
        ("solver", "nutrition_solver"), ("ai-assistant", "ai_assistant"),
        ("admin-operations", "admin_operations"), ("admin-analytics", "admin_analytics"),
        ("account", "accounts"), ("onboarding", "accounts"), ("mcp", "mcp"),
        ("docs", "documentation"), ("export", "documentation"), ("ui", "design"),
    )
    for token, domain in domain_tokens:
        if token in filename:
            return domain
    return "cross_cutting"
