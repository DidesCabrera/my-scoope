from dataclasses import dataclass, field
from datetime import datetime

from admin_analytics.filters import AdminAnalyticsFilters


@dataclass(frozen=True)
class AdminAnalyticsModuleVM:
    title: str
    description: str
    icon: str
    status: str


@dataclass(frozen=True)
class AdminAnalyticsKpiVM:
    label: str
    value: str
    helper: str = ""


@dataclass(frozen=True)
class AdminAnalyticsSectionVM:
    title: str
    description: str
    kpis: list[AdminAnalyticsKpiVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsHealthSignalVM:
    label: str
    status: str
    value: str
    description: str


@dataclass(frozen=True)
class AdminAnalyticsOverviewVM:
    title: str
    subtitle: str
    north_star_metric: str
    north_star_description: str
    north_star_value: str = "—"
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    health_signals: list[AdminAnalyticsHealthSignalVM] = field(default_factory=list)
    modules: list[AdminAnalyticsModuleVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsAccountPlanRowVM:
    slug: str
    name: str
    status: str
    included_monthly_credits: str
    daily_credit_limit: str
    monthly_credit_limit: str
    active_subscriptions: str


@dataclass(frozen=True)
class AdminAnalyticsAccountWalletRowVM:
    email: str
    username: str
    balance: str
    reserved_balance: str
    available_credits: str
    period: str
    plan_snapshot_code: str


@dataclass(frozen=True)
class AdminAnalyticsLedgerKindRowVM:
    kind: str
    entries: str
    credits_delta: str
    reserved_delta: str


@dataclass(frozen=True)
class AdminAnalyticsAccountsVM:
    title: str
    subtitle: str
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    plan_rows: list[AdminAnalyticsAccountPlanRowVM] = field(default_factory=list)
    active_subscriptions_by_plan: list[AdminAnalyticsKpiVM] = field(default_factory=list)
    wallet_rows: list[AdminAnalyticsAccountWalletRowVM] = field(default_factory=list)
    ledger_kind_rows: list[AdminAnalyticsLedgerKindRowVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsAIAssistantActionRowVM:
    action_type: str
    events: str
    completed: str
    errors: str
    blocked: str
    total_tokens: str
    estimated_cost_usd: str
    charged_credits: str
    tool_calls: str


@dataclass(frozen=True)
class AdminAnalyticsAIAssistantModelRowVM:
    provider: str
    model_name: str
    events: str
    total_tokens: str
    estimated_cost_usd: str
    charged_credits: str
    avg_latency_ms: str


@dataclass(frozen=True)
class AdminAnalyticsAIAssistantCreditPlanRowVM:
    credit_plan_code: str
    events: str
    active_users: str
    charged_credits: str
    estimated_cost_usd: str


@dataclass(frozen=True)
class AdminAnalyticsAIAssistantUserRowVM:
    email: str
    username: str
    events: str
    total_tokens: str
    estimated_cost_usd: str
    charged_credits: str
    blocked: str
    errors: str


@dataclass(frozen=True)
class AdminAnalyticsAIAssistantQuotaRowVM:
    email: str
    username: str
    plan_code: str
    credits_used: str
    monthly_credit_limit: str
    daily_credit_limit: str
    usage_ratio: str
    hard_blocked: str


@dataclass(frozen=True)
class AdminAnalyticsAIAssistantVM:
    title: str
    subtitle: str
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    current_period: str = ""
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    health_signals: list[AdminAnalyticsHealthSignalVM] = field(default_factory=list)
    action_rows: list[AdminAnalyticsAIAssistantActionRowVM] = field(default_factory=list)
    model_rows: list[AdminAnalyticsAIAssistantModelRowVM] = field(default_factory=list)
    credit_plan_rows: list[AdminAnalyticsAIAssistantCreditPlanRowVM] = field(default_factory=list)
    user_rows: list[AdminAnalyticsAIAssistantUserRowVM] = field(default_factory=list)
    quota_rows: list[AdminAnalyticsAIAssistantQuotaRowVM] = field(default_factory=list)
    ledger_kind_rows: list[AdminAnalyticsLedgerKindRowVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsProductEntityRowVM:
    entity: str
    total: str
    created_7d: str
    created_30d: str
    draft: str
    public: str
    forked: str
    usage: str


@dataclass(frozen=True)
class AdminAnalyticsProductSourceRowVM:
    source: str
    total: str
    created_7d: str


@dataclass(frozen=True)
class AdminAnalyticsProductComparisonRowVM:
    kind: str
    total: str
    updated_7d: str
    owners: str


@dataclass(frozen=True)
class AdminAnalyticsProductShareRowVM:
    label: str
    sent_total: str
    sent_7d: str
    sent_30d: str
    accepted_total: str
    unread_total: str
    favorite_total: str
    removed_total: str


@dataclass(frozen=True)
class AdminAnalyticsProductBuilderRowVM:
    email: str
    username: str
    meals: str
    dailyplans: str
    programs: str
    shares: str
    comparisons: str
    applied_proposals: str
    score: str


@dataclass(frozen=True)
class AdminAnalyticsProgramWeekRowVM:
    week_number: str
    slots: str
    programs: str


@dataclass(frozen=True)
class AdminAnalyticsProductActivityVM:
    title: str
    subtitle: str
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    health_signals: list[AdminAnalyticsHealthSignalVM] = field(default_factory=list)
    entity_rows: list[AdminAnalyticsProductEntityRowVM] = field(default_factory=list)
    source_rows: list[AdminAnalyticsProductSourceRowVM] = field(default_factory=list)
    comparison_rows: list[AdminAnalyticsProductComparisonRowVM] = field(default_factory=list)
    share_rows: list[AdminAnalyticsProductShareRowVM] = field(default_factory=list)
    builder_rows: list[AdminAnalyticsProductBuilderRowVM] = field(default_factory=list)
    program_week_rows: list[AdminAnalyticsProgramWeekRowVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogStatusRowVM:
    status: str
    total: str
    created_7d: str
    avg_quality: str
    solver_enabled: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogSourceRowVM:
    source_type: str
    total: str
    created_7d: str
    avg_quality: str
    published: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogEvidenceRowVM:
    label: str
    total: str
    foods_missing: str
    created_7d: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogLicenseRowVM:
    license_status: str
    total: str
    foods: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogImportStatusRowVM:
    status: str
    total: str
    rows: str
    imported: str
    skipped: str
    failed: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogImportSourceRowVM:
    source_type: str
    total: str
    completed: str
    failed: str
    imported: str
    failed_rows: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogProviderReferenceRowVM:
    provider: str
    references: str
    active: str
    selected: str
    seen: str
    expired: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogProviderFetchRowVM:
    provider: str
    lookup_type: str
    total: str
    success: str
    failed: str
    success_rate: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogCandidateStatusRowVM:
    status: str
    total: str
    avg_priority: str
    created_7d: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogCandidateReasonRowVM:
    reason: str
    total: str
    avg_priority: str


@dataclass(frozen=True)
class AdminAnalyticsFoodCatalogVM:
    title: str
    subtitle: str
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    health_signals: list[AdminAnalyticsHealthSignalVM] = field(default_factory=list)
    status_rows: list[AdminAnalyticsFoodCatalogStatusRowVM] = field(default_factory=list)
    source_rows: list[AdminAnalyticsFoodCatalogSourceRowVM] = field(default_factory=list)
    evidence_rows: list[AdminAnalyticsFoodCatalogEvidenceRowVM] = field(default_factory=list)
    license_rows: list[AdminAnalyticsFoodCatalogLicenseRowVM] = field(default_factory=list)
    import_status_rows: list[AdminAnalyticsFoodCatalogImportStatusRowVM] = field(default_factory=list)
    import_source_rows: list[AdminAnalyticsFoodCatalogImportSourceRowVM] = field(default_factory=list)
    provider_reference_rows: list[AdminAnalyticsFoodCatalogProviderReferenceRowVM] = field(default_factory=list)
    provider_fetch_rows: list[AdminAnalyticsFoodCatalogProviderFetchRowVM] = field(default_factory=list)
    candidate_status_rows: list[AdminAnalyticsFoodCatalogCandidateStatusRowVM] = field(default_factory=list)
    candidate_reason_rows: list[AdminAnalyticsFoodCatalogCandidateReasonRowVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsSolverStatusRowVM:
    status: str
    total: str


@dataclass(frozen=True)
class AdminAnalyticsSolverReasonRowVM:
    reason_code: str
    total: str


@dataclass(frozen=True)
class AdminAnalyticsSolverWorstMacroRowVM:
    macro: str
    total: str


@dataclass(frozen=True)
class AdminAnalyticsSolverSourceRowVM:
    source: str
    total: str
    optimal: str
    acceptable: str
    partial: str
    impossible: str
    avg_score: str


@dataclass(frozen=True)
class AdminAnalyticsSolverIssueRowVM:
    severity: str
    code: str
    metric: str
    total: str


@dataclass(frozen=True)
class AdminAnalyticsSolverTargetMetricRowVM:
    metric: str
    samples: str
    avg_abs_diff_percent: str
    max_abs_diff_percent: str


@dataclass(frozen=True)
class AdminAnalyticsSolverCatalogStatusRowVM:
    status: str
    total: str
    high_quality: str


@dataclass(frozen=True)
class AdminAnalyticsSolverOperationalGroupRowVM:
    food_group: str
    total: str
    verified: str


@dataclass(frozen=True)
class AdminAnalyticsSolverConfigRowVM:
    group: str
    key: str
    value: str


@dataclass(frozen=True)
class AdminAnalyticsNutritionSolverVM:
    title: str
    subtitle: str
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    health_signals: list[AdminAnalyticsHealthSignalVM] = field(default_factory=list)
    solver_status_rows: list[AdminAnalyticsSolverStatusRowVM] = field(default_factory=list)
    solver_reason_rows: list[AdminAnalyticsSolverReasonRowVM] = field(default_factory=list)
    solver_worst_macro_rows: list[AdminAnalyticsSolverWorstMacroRowVM] = field(default_factory=list)
    solver_source_rows: list[AdminAnalyticsSolverSourceRowVM] = field(default_factory=list)
    engine_status_rows: list[AdminAnalyticsSolverStatusRowVM] = field(default_factory=list)
    issue_rows: list[AdminAnalyticsSolverIssueRowVM] = field(default_factory=list)
    target_metric_rows: list[AdminAnalyticsSolverTargetMetricRowVM] = field(default_factory=list)
    catalog_status_rows: list[AdminAnalyticsSolverCatalogStatusRowVM] = field(default_factory=list)
    operational_group_rows: list[AdminAnalyticsSolverOperationalGroupRowVM] = field(default_factory=list)
    config_rows: list[AdminAnalyticsSolverConfigRowVM] = field(default_factory=list)

@dataclass(frozen=True)
class AdminAnalyticsAlertVM:
    severity: str
    domain: str
    title: str
    value: str
    description: str
    recommendation: str


@dataclass(frozen=True)
class AdminAnalyticsAlertGroupVM:
    title: str
    description: str
    alerts: list[AdminAnalyticsAlertVM] = field(default_factory=list)


@dataclass(frozen=True)
class AdminAnalyticsAlertsVM:
    title: str
    subtitle: str
    generated_at: datetime | None = None
    period_label: str = "Últimos 7 días"
    filters: AdminAnalyticsFilters = field(default_factory=AdminAnalyticsFilters)
    sections: list[AdminAnalyticsSectionVM] = field(default_factory=list)
    health_signals: list[AdminAnalyticsHealthSignalVM] = field(default_factory=list)
    alert_groups: list[AdminAnalyticsAlertGroupVM] = field(default_factory=list)
    alerts: list[AdminAnalyticsAlertVM] = field(default_factory=list)
