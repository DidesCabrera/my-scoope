from __future__ import annotations

from dataclasses import dataclass, field

from core.project_status import build_project_status


@dataclass(frozen=True)
class SystemControlMetricVM:
    label: str
    value: str
    helper: str
    icon: str


@dataclass(frozen=True)
class SystemControlFindingVM:
    status: str
    code: str
    summary: str
    action: str = ""


@dataclass(frozen=True)
class SystemControlProbeVM:
    code: str
    status: str
    rows: list[tuple[str, str]] = field(default_factory=list)
    message: str = ""


@dataclass(frozen=True)
class SystemControlCapabilityVM:
    domain: str
    rows: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class SystemControlVM:
    title: str = "Project Control"
    subtitle: str = (
        "Estado ejecutable y de sólo lectura sobre ambiente, release, migraciones, "
        "capacidades e inventarios seguros de My Scoope."
    )
    period_label: str = "PCF05 · Read-only control plane"
    current_period: str = "Project Control"
    overall_status: str = "unknown"
    generated_at: str = ""
    metrics: list[SystemControlMetricVM] = field(default_factory=list)
    findings: list[SystemControlFindingVM] = field(default_factory=list)
    probes: list[SystemControlProbeVM] = field(default_factory=list)
    capabilities: list[SystemControlCapabilityVM] = field(default_factory=list)


def build_system_control_vm() -> SystemControlVM:
    report = build_project_status().as_dict()
    release = report["release"]
    environment = report["environment"]
    deployment_environment = (
        release["service"] if release["service"] != "unknown" else environment["name"]
    )
    migration_probe = next(
        (probe for probe in report["probes"] if probe["code"] == "database.migrations"),
        {"status": "error", "data": {}},
    )
    pending_count = migration_probe["data"].get("pending_count", "?")

    findings = [
        SystemControlFindingVM(
            status=item["status"],
            code=item["code"],
            summary=item["summary"],
            action=item.get("action", ""),
        )
        for item in environment.get("attention", [])
    ]
    if not release["identity_configured"]:
        findings.append(SystemControlFindingVM(
            status="warning",
            code="release.identity",
            summary="The deployed commit identity is not configured in this environment.",
            action="Set RENDER_GIT_COMMIT or SENTRY_RELEASE during deployment.",
        ))
    for probe in report["probes"]:
        if probe["status"] != "ok":
            findings.append(SystemControlFindingVM(
                status=probe["status"],
                code=probe["code"],
                summary=probe["message"] or "This project-status probe needs attention.",
            ))

    return SystemControlVM(
        overall_status=str(report["status"]),
        generated_at=str(report["generated_at"]),
        metrics=[
            SystemControlMetricVM(
                label="Ambiente",
                value=str(deployment_environment),
                helper=f"Perfil {environment['name']} · {environment['settings_module']}",
                icon="server-cog",
            ),
            SystemControlMetricVM(
                label="Release",
                value=str(release["commit"])[:12],
                helper="Identidad desplegada" if release["identity_configured"] else "Identidad pendiente",
                icon="git-commit-horizontal",
            ),
            SystemControlMetricVM(
                label="Migraciones pendientes",
                value=str(pending_count),
                helper=f"Database: {migration_probe['data'].get('database_vendor', 'unknown')}",
                icon="database-zap",
            ),
            SystemControlMetricVM(
                label="Atención",
                value=str(len(findings)),
                helper=f"Estado general: {report['status']}",
                icon="circle-alert",
            ),
        ],
        findings=findings,
        probes=[
            SystemControlProbeVM(
                code=probe["code"],
                status=probe["status"],
                rows=[(str(key), _display_value(value)) for key, value in probe["data"].items()],
                message=probe["message"],
            )
            for probe in report["probes"]
        ],
        capabilities=[
            SystemControlCapabilityVM(
                domain=domain.replace("_", " ").title(),
                rows=[(str(key), _display_value(value)) for key, value in values.items()],
            )
            for domain, values in report["capabilities"].items()
        ],
    )


def _display_value(value: object) -> str:
    if isinstance(value, bool):
        return "enabled" if value else "disabled"
    return str(value)
