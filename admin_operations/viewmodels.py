from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AdminOperationsMetricVM:
    label: str
    value: str
    helper: str = ""
    icon: str = "activity"


@dataclass(frozen=True)
class AdminOperationsQueueVM:
    title: str
    description: str
    icon: str
    status: str
    href: str = "#"
    count: str = "0"
    priority: str = "info"
    helper: str = ""
    primary_action_label: str = "Ver cola"
    is_enabled: bool = False


@dataclass(frozen=True)
class AdminOperationsPrincipleVM:
    title: str
    description: str
    icon: str


@dataclass(frozen=True)
class AdminOperationsWarningVM:
    title: str
    domain: str
    description: str
    value: str
    severity: str = "info"
    href: str = "#"


@dataclass(frozen=True)
class AdminOperationsOverviewVM:
    title: str = "Colas accionables para operar My Scoope"
    subtitle: str = (
        "Este overview convierte señales internas en colas de trabajo staff-only. "
        "Food Catalog, Accounts, AI Assistant y Audit Log abren workflows guiados."
    )
    period_label: str = "OPS02 · Action queues"
    current_period: str = "Admin Operations V1"
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    queues: list[AdminOperationsQueueVM] = field(default_factory=list)
    warnings: list[AdminOperationsWarningVM] = field(default_factory=list)
    principles: list[AdminOperationsPrincipleVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsCandidateVM:
    pk: int
    title: str
    brand_name: str
    provider: str
    status: str
    reason: str
    priority: int
    demand_label: str
    source_url: str = ""
    detail_url: str = "#"
    admin_url: str = "#"
    notes: str = ""
    reviewed_label: str = "Sin revisión"


@dataclass(frozen=True)
class AdminOperationsCatalogFoodVM:
    pk: int
    title: str
    brand_name: str
    status: str
    source_type: str
    quality_score: int
    solver_enabled: bool
    macro_label: str
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsFoodCatalogVM:
    title: str = "Curación operacional del Food Catalog"
    subtitle: str = (
        "Permite revisar candidatos externos, aprobarlos para curación, pedir evidencia "
        "o rechazarlos con razón obligatoria."
    )
    period_label: str = "OPS03 · Food Catalog operations"
    current_period: str = "OPS03 · Food Catalog"
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    candidates: list[AdminOperationsCandidateVM] = field(default_factory=list)
    catalog_foods: list[AdminOperationsCatalogFoodVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsCatalogCoverageVM:
    label: str
    total: str
    share_label: str
    helper: str = ""


@dataclass(frozen=True)
class AdminOperationsCatalogInventoryFoodVM:
    pk: int
    title: str
    identity_lines: list[str]
    classification_lines: list[str]
    governance_lines: list[str]
    nutrition_lines: list[str]
    functional_lines: list[str]
    solver_lines: list[str]
    quality_lines: list[str]
    relation_lines: list[str]
    lifecycle_lines: list[str]
    admin_url: str


@dataclass(frozen=True)
class AdminOperationsCatalogInventoryVM:
    title: str = "Inventario y calidad del Food Catalog"
    subtitle: str = (
        "Visibilidad completa y de sólo lectura sobre los alimentos master persistidos, "
        "su cobertura nutricional, taxonomía, trazabilidad y preparación para el solver."
    )
    period_label: str = "Food Catalog · Observability"
    current_period: str = "Inventario y calidad"
    query: str = ""
    selected_status: str = ""
    selected_source: str = ""
    selected_group: str = ""
    selected_solver_state: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    nutrition_metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    gap_metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    category_coverage: list[AdminOperationsCatalogCoverageVM] = field(default_factory=list)
    source_coverage: list[AdminOperationsCatalogCoverageVM] = field(default_factory=list)
    foods: list[AdminOperationsCatalogInventoryFoodVM] = field(default_factory=list)
    status_options: list[tuple[str, str]] = field(default_factory=list)
    source_options: list[tuple[str, str]] = field(default_factory=list)
    group_options: list[str] = field(default_factory=list)
    filtered_total: str = "0"
    page_label: str = "Página 1 de 1"
    previous_url: str = ""
    next_url: str = ""


@dataclass(frozen=True)
class AdminOperationsCatalogImportBatchVM:
    pk: int
    run_type: str
    source_label: str
    status: str
    version: str
    counts_label: str
    operator_label: str
    reason: str
    input_hash_label: str
    dry_run_label: str
    started_label: str


@dataclass(frozen=True)
class AdminOperationsCatalogImportsVM:
    title: str = "Imports y dry-runs del Food Catalog"
    subtitle: str = (
        "Cockpit staff-only para verificar trazabilidad, equivalencia e idempotencia antes de operar cada fuente."
    )
    period_label: str = "FCG02 · Import control plane"
    current_period: str = "Imports y dry-runs"
    selected_source: str = ""
    selected_status: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    batches: list[AdminOperationsCatalogImportBatchVM] = field(default_factory=list)
    source_options: list[tuple[str, str]] = field(default_factory=list)
    status_options: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsCandidateDetailVM:
    title: str
    subtitle: str
    period_label: str = "OPS03 · Candidate review"
    current_period: str = "OPS03 · Food Catalog"
    candidate: AdminOperationsCandidateVM | None = None
    allowed_actions: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsCreditWalletVM:
    user_id: int
    user_label: str
    email: str
    balance: str
    reserved_balance: str
    available_credits: str
    period: str
    plan_snapshot_code: str
    subscription_label: str = "Sin suscripción activa"
    detail_url: str = "#"
    admin_url: str = "#"
    has_reserved_credits: bool = False


@dataclass(frozen=True)
class AdminOperationsCreditLedgerVM:
    pk: int
    created_label: str
    kind: str
    credits_delta: str
    reserved_delta: str
    balance_after: str
    reserved_balance_after: str
    reference_label: str
    reason: str


@dataclass(frozen=True)
class AdminOperationsCreditReservationVM:
    pk: int
    user_id: int
    user_label: str
    email: str
    credits: str
    reference_type: str
    reference_id: str
    reference_label: str
    created_label: str
    reason: str
    detail_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAccountsVM:
    title: str = "Operaciones de cuentas y créditos"
    subtitle: str = (
        "Revisión staff-only de wallets, reservas abiertas y contexto comercial antes "
        "de ajustes manuales."
    )
    period_label: str = "OPS04 · Accounts and credits operations"
    current_period: str = "OPS04 · Accounts & Credits"
    query: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    wallets: list[AdminOperationsCreditWalletVM] = field(default_factory=list)
    reservations: list[AdminOperationsCreditReservationVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsAccountDetailVM:
    title: str
    subtitle: str
    period_label: str = "OPS04 · Account wallet review"
    current_period: str = "OPS04 · Accounts & Credits"
    wallet: AdminOperationsCreditWalletVM | None = None
    ledger_entries: list[AdminOperationsCreditLedgerVM] = field(default_factory=list)
    reservations: list[AdminOperationsCreditReservationVM] = field(default_factory=list)
@dataclass(frozen=True)
class AdminOperationsAIEventVM:
    pk: int
    created_label: str
    user_label: str
    email: str
    status: str
    action_type: str
    provider_label: str
    model_name: str
    error_type: str
    tokens_label: str
    credits_label: str
    metadata_state: str
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAIProposalVM:
    pk: int
    title: str
    source: str
    status: str
    created_label: str
    created_by_label: str
    dailyplan_label: str
    summary: str
    detail_url: str = "#"
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAIQuotaVM:
    pk: int
    user_id: int
    user_label: str
    email: str
    period: str
    plan_code: str
    usage_label: str
    daily_limit: str
    hard_blocked: bool
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsAIVM:
    title: str = "Operaciones de AI Assistant"
    subtitle: str = (
        "Revisión staff-only de errores, bloqueos, propuestas AI/MCP pendientes y "
        "cuotas que pueden explicar restricciones de acceso."
    )
    period_label: str = "OPS05 · AI Assistant operations"
    current_period: str = "OPS05 · AI Assistant"
    query: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    events: list[AdminOperationsAIEventVM] = field(default_factory=list)
    proposals: list[AdminOperationsAIProposalVM] = field(default_factory=list)
    quotas: list[AdminOperationsAIQuotaVM] = field(default_factory=list)



@dataclass(frozen=True)
class AdminOperationsAuditEventVM:
    pk: int
    created_label: str
    actor_label: str
    action: str
    target_label: str
    target_type: str
    target_id: str
    status_before: str
    status_after: str
    reason: str
    metadata_summary: str


@dataclass(frozen=True)
class AdminOperationsAuditLogVM:
    title: str = "Audit log operacional"
    subtitle: str = (
        "Registro append-only de acciones staff ejecutadas desde Admin Operations. "
        "Consolida trazabilidad operacional transversal sin reemplazar los ledgers de dominio."
    )
    period_label: str = "OPS06 · Operational audit log"
    current_period: str = "OPS06 · Audit Log"
    query: str = ""
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    events: list[AdminOperationsAuditEventVM] = field(default_factory=list)
