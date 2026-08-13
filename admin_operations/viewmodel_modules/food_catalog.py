from __future__ import annotations

from dataclasses import dataclass, field

from admin_operations.viewmodel_modules.common import AdminOperationsMetricVM


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
    stage_label: str
    action_buttons: list[tuple[str, str]]
    source_type: str
    quality_score: int
    solver_enabled: bool
    macro_label: str
    admin_url: str = "#"


@dataclass(frozen=True)
class AdminOperationsDetailFactVM:
    label: str
    value: str
    helper: str = ""


@dataclass(frozen=True)
class AdminOperationsCatalogEvidenceVM:
    name: str
    source_type: str
    license_label: str
    reference_label: str
    dataset_label: str = ""
    url: str = ""
    attribution: str = ""


@dataclass(frozen=True)
class AdminOperationsCatalogPortionVM:
    label: str
    grams_label: str
    source_label: str
    is_default: bool = False


@dataclass(frozen=True)
class AdminOperationsCatalogAliasVM:
    name: str
    kind_label: str
    locale_label: str
    is_primary: bool = False


@dataclass(frozen=True)
class AdminOperationsCatalogFoodDetailVM:
    title: str
    subtitle: str
    food_pk: int
    display_name: str
    brand_name: str
    stage_key: str
    stage_label: str
    status_label: str
    source_label: str
    quality_score: int
    confidence_label: str
    readiness_state: str
    readiness_label: str
    period_label: str = "Food Catalog · Ficha de curación"
    current_period: str = "Detalle de alimento"
    readiness_issues: list[str] = field(default_factory=list)
    identity_facts: list[AdminOperationsDetailFactVM] = field(default_factory=list)
    nutrition_facts: list[AdminOperationsDetailFactVM] = field(default_factory=list)
    solver_facts: list[AdminOperationsDetailFactVM] = field(default_factory=list)
    lifecycle_facts: list[AdminOperationsDetailFactVM] = field(default_factory=list)
    evidence: list[AdminOperationsCatalogEvidenceVM] = field(default_factory=list)
    portions: list[AdminOperationsCatalogPortionVM] = field(default_factory=list)
    aliases: list[AdminOperationsCatalogAliasVM] = field(default_factory=list)
    admin_url: str = ""
    action_url: str = ""
    snapshot_url: str = ""
    primary_action_kind: str = "none"
    primary_action_value: str = ""
    primary_action_label: str = ""
    primary_action_icon: str = "arrow-right"
    secondary_actions: list[tuple[str, str]] = field(default_factory=list)
    is_operational: bool = False
    operational_label: str = ""
    operational_url: str = ""


@dataclass(frozen=True)
class AdminOperationsCurationStageVM:
    key: str
    label: str
    helper: str
    count: str
    icon: str
    url: str
    is_active: bool = False


@dataclass(frozen=True)
class AdminOperationsCurationItemVM:
    kind: str
    pk: int
    title: str
    brand_name: str
    origin_label: str
    stage_key: str
    stage_label: str
    status: str
    status_label: str
    detail_label: str
    context_label: str
    readiness_state: str
    readiness_label: str
    readiness_issues: list[str] = field(default_factory=list)
    quality_score: int | None = None
    detail_url: str = ""
    admin_url: str = ""
    action_url: str = ""
    primary_action_value: str = ""
    primary_action_label: str = ""
    primary_action_icon: str = "arrow-right"
    primary_action_kind: str = "link"
    secondary_actions: list[tuple[str, str]] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsFoodCatalogVM:
    title: str = "Curación del Food Catalog"
    subtitle: str = (
        "Una sola bandeja para revisar cada entrada, resolver sus datos y convertirla "
        "en un alimento operativo."
    )
    period_label: str = "Food Catalog · Curación"
    current_period: str = "Bandeja de curación"
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    candidates: list[AdminOperationsCandidateVM] = field(default_factory=list)
    catalog_foods: list[AdminOperationsCatalogFoodVM] = field(default_factory=list)
    stages: list[AdminOperationsCurationStageVM] = field(default_factory=list)
    work_items: list[AdminOperationsCurationItemVM] = field(default_factory=list)
    query: str = ""
    selected_stage: str = "all"
    selected_sort: str = "quality_asc"
    sort_options: list[tuple[str, str]] = field(default_factory=list)
    filtered_total: str = "0"
    preparation_total: str = "0"
    preparation_food_total: str = "0"
    blocked_total: str = "0"
    operational_total: str = "0"


@dataclass(frozen=True)
class AdminOperationsCatalogCoverageVM:
    label: str
    total: str
    share_label: str
    helper: str = ""


@dataclass(frozen=True)
class AdminOperationsCatalogDataCoverageRowVM:
    label: str
    existing_total: str
    share_label: str


@dataclass(frozen=True)
class AdminOperationsCatalogDataCoverageVM:
    title: str = "Cobertura de datos del Food Catalog"
    subtitle: str = "Cobertura campo por campo sobre todos los alimentos persistidos."
    total_foods: str = "0"
    selected_section: str = "identity"
    sections: list[AdminOperationsCatalogInventorySectionVM] = field(default_factory=list)
    rows: list[AdminOperationsCatalogDataCoverageRowVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsCatalogInventorySectionVM:
    key: str
    label: str
    icon: str
    url: str
    is_active: bool = False


@dataclass(frozen=True)
class AdminOperationsCatalogInventoryColumnVM:
    key: str
    label: str


@dataclass(frozen=True)
class AdminOperationsCatalogInventoryCellVM:
    value: str
    label: str = ""
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
    inventory_cells: list[AdminOperationsCatalogInventoryCellVM] = field(default_factory=list)


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
    target_funnel: list[AdminOperationsMetricVM] = field(default_factory=list)
    target_category_coverage: list[AdminOperationsCatalogCoverageVM] = field(default_factory=list)
    target_version_label: str = ""
    foods: list[AdminOperationsCatalogInventoryFoodVM] = field(default_factory=list)
    inventory_sections: list[AdminOperationsCatalogInventorySectionVM] = field(default_factory=list)
    selected_inventory_section: str = "identity"
    inventory_columns: list[AdminOperationsCatalogInventoryColumnVM] = field(default_factory=list)
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
class AdminOperationsCatalogEnrichmentBatchVM:
    batch_ref: str
    environment: str
    status: str
    counts_label: str
    reason: str
    contract_label: str
    created_label: str


@dataclass(frozen=True)
class AdminOperationsReadinessFoodVM:
    pk: int
    title: str
    status_label: str
    source_label: str
    missing_label: str
    detail_url: str


@dataclass(frozen=True)
class AdminOperationsReadinessBatchVM:
    batch_ref: str
    status: str
    environment: str
    counts_label: str
    reason: str
    created_label: str
    detail_url: str


@dataclass(frozen=True)
class AdminOperationsReadinessProposalVM:
    field_label: str
    current_label: str
    proposed_label: str
    policy_label: str
    confidence_label: str
    rationale: str
    evidence: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsReadinessProposalGroupVM:
    food_pk: int
    title: str
    status_label: str
    source_label: str
    source_url: str
    food_detail_url: str
    proposals: list[AdminOperationsReadinessProposalVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminOperationsReadinessVM:
    title: str = "Readiness del Food Catalog"
    subtitle: str = "Preparación, auditoría y aplicación trazable de datos internos sin publicación automática."
    period_label: str = "Food Catalog · Readiness"
    current_period: str = "Control de readiness"
    metrics: list[AdminOperationsMetricVM] = field(default_factory=list)
    foods: list[AdminOperationsReadinessFoodVM] = field(default_factory=list)
    batches: list[AdminOperationsReadinessBatchVM] = field(default_factory=list)
    audit_passes: bool = False
    source_backfill_pending: int = 0


@dataclass(frozen=True)
class AdminOperationsReadinessBatchDetailVM:
    title: str
    subtitle: str
    period_label: str = "Food Catalog · Readiness"
    current_period: str = "Revisión de lote"
    batch_ref: str = ""
    status: str = ""
    environment: str = ""
    reason: str = ""
    counts_label: str = ""
    manifest_hash_label: str = ""
    groups: list[AdminOperationsReadinessProposalGroupVM] = field(default_factory=list)
    action_url: str = ""
    can_apply: bool = False
    can_revert: bool = False


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
    enrichment_batches: list[AdminOperationsCatalogEnrichmentBatchVM] = field(default_factory=list)
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




__all__ = ['AdminOperationsCandidateVM', 'AdminOperationsCatalogFoodVM', 'AdminOperationsDetailFactVM', 'AdminOperationsCatalogEvidenceVM', 'AdminOperationsCatalogPortionVM', 'AdminOperationsCatalogAliasVM', 'AdminOperationsCatalogFoodDetailVM', 'AdminOperationsCurationStageVM', 'AdminOperationsCurationItemVM', 'AdminOperationsFoodCatalogVM', 'AdminOperationsCatalogCoverageVM', 'AdminOperationsCatalogDataCoverageRowVM', 'AdminOperationsCatalogDataCoverageVM', 'AdminOperationsCatalogInventorySectionVM', 'AdminOperationsCatalogInventoryColumnVM', 'AdminOperationsCatalogInventoryCellVM', 'AdminOperationsCatalogInventoryFoodVM', 'AdminOperationsCatalogInventoryVM', 'AdminOperationsCatalogImportBatchVM', 'AdminOperationsCatalogEnrichmentBatchVM', 'AdminOperationsReadinessFoodVM', 'AdminOperationsReadinessBatchVM', 'AdminOperationsReadinessProposalVM', 'AdminOperationsReadinessProposalGroupVM', 'AdminOperationsReadinessVM', 'AdminOperationsReadinessBatchDetailVM', 'AdminOperationsCatalogImportsVM', 'AdminOperationsCandidateDetailVM']
