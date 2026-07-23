from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import models
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from accounts.models import AccountSubscription, CreditLedger, CreditWallet
from ai_assistant.models import AIUsageEvent, AIUserCreditQuota
from billing.models import BillingEvent, ProviderSubscription, TaxDocument
from food_catalog.application.coverage_manifest import load_coverage_manifest
from food_catalog.models import CatalogCurationCandidate, CatalogFood, CatalogFoodSource, CatalogImportBatch
from notas.domain.model_modules.proposals import NutritionProposal
from admin_operations.models import AdminOperationAuditEvent

CATALOG_CANDIDATE_ACTION_STATUSES = [
    CatalogCurationCandidate.STATUS_QUEUED,
    CatalogCurationCandidate.STATUS_IN_REVIEW,
    CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
]

CATALOG_FOOD_REVIEW_STATUSES = [
    CatalogFood.STATUS_EXTERNAL_CANDIDATE,
    CatalogFood.STATUS_MANUAL_CANDIDATE,
    CatalogFood.STATUS_BRAND_SUBMITTED,
    CatalogFood.STATUS_NORMALIZED,
    CatalogFood.STATUS_PENDING_REVIEW,
    CatalogFood.STATUS_NEEDS_MORE_EVIDENCE,
    CatalogFood.STATUS_REVIEWED,
    CatalogFood.STATUS_VERIFIED,
    CatalogFood.STATUS_PUBLISHED,
]

CATALOG_GROUP_FAMILIES = (
    ("vegetables", "Verduras", {"vegetable", "vegetables", "verdura", "verduras", "hortalizas"}),
    ("protein", "Proteínas", {"protein", "proteins", "proteina", "proteinas", "proteína", "proteínas", "meat", "meats", "carne", "carnes", "fish", "pescado", "pescados", "poultry", "aves"}),
    ("fruit", "Frutas", {"fruit", "fruits", "fruta", "frutas"}),
    ("cereals", "Cereales", {"cereal", "cereals", "grain", "grains", "cereal", "cereales"}),
    ("legumes", "Legumbres", {"legume", "legumes", "legumbre", "legumbres"}),
    ("dairy", "Lácteos", {"dairy", "dairies", "lacteo", "lacteos", "lácteo", "lácteos"}),
    ("tubers", "Tubérculos", {"tuber", "tubers", "tuberculo", "tuberculos", "tubérculo", "tubérculos"}),
    ("fats", "Grasas", {"fat", "fats", "oil", "oils", "grasa", "grasas", "aceite", "aceites"}),
)

AI_OPERATIONAL_STATUSES = [
    AIUsageEvent.Status.ERROR,
    AIUsageEvent.Status.BLOCKED,
]


def get_operations_overview_metrics() -> dict:
    now = timezone.now()
    since_7d = now - timedelta(days=7)

    candidate_qs = CatalogCurationCandidate.objects.filter(status__in=CATALOG_CANDIDATE_ACTION_STATUSES)
    catalog_food_qs = CatalogFood.objects.filter(status__in=CATALOG_FOOD_REVIEW_STATUSES)
    ai_issue_qs = AIUsageEvent.objects.filter(status__in=AI_OPERATIONAL_STATUSES, created_at__gte=since_7d)
    proposal_review_qs = NutritionProposal.objects.filter(
        source__in=[NutritionProposal.SOURCE_AI, NutritionProposal.SOURCE_MCP],
        status=NutritionProposal.STATUS_PENDING_REVIEW,
    )
    wallet_qs = CreditWallet.objects.filter(reserved_balance__gt=0)
    billing = {
        "failed_events": BillingEvent.objects.filter(status=BillingEvent.Status.FAILED).count(),
        "past_due_subscriptions": ProviderSubscription.objects.filter(status=ProviderSubscription.Status.PAST_DUE).count(),
        "failed_tax_documents": TaxDocument.objects.filter(status__in=[TaxDocument.Status.FAILED, TaxDocument.Status.REJECTED]).count(),
        "tax_adjustments": TaxDocument.objects.filter(adjustment_required=True).count(),
    }

    catalog = {
        "pending_candidates": candidate_qs.count(),
        "high_priority_candidates": candidate_qs.filter(priority__gte=75).count(),
        "needs_more_evidence_candidates": candidate_qs.filter(
            status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE,
        ).count(),
        "catalog_foods_requiring_review": catalog_food_qs.count(),
    }

    ai = ai_issue_qs.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        blocked=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
    )
    ai.update({
        "pending_ai_proposals": proposal_review_qs.count(),
    })

    accounts = wallet_qs.aggregate(
        wallets_with_reserved_credits=Count("id"),
        reserved_credits_total=Sum("reserved_balance"),
    )
    accounts["reserved_credits_total"] = accounts["reserved_credits_total"] or 0

    warnings = _build_warning_candidates(catalog=catalog, ai=ai, accounts=accounts)

    return {
        "generated_at": now,
        "period_label": "Últimos 7 días · señales operacionales",
        "catalog": catalog,
        "ai": ai,
        "accounts": accounts,
        "billing": billing,
        "warnings": warnings,
    }


def get_food_catalog_operations_payload(*, limit: int = 25) -> dict:
    """Return actionable Food Catalog queues for OPS03.

    The payload is deliberately read-model oriented. Mutations are handled by
    explicit services so templates never perform direct model changes.
    """

    candidate_qs = CatalogCurationCandidate.objects.filter(
        status__in=CATALOG_CANDIDATE_ACTION_STATUSES,
    ).select_related("reviewed_by").order_by("-priority", "status", "display_name")

    catalog_food_qs = CatalogFood.objects.filter(
        status__in=CATALOG_FOOD_REVIEW_STATUSES,
    ).order_by("status", "-data_quality_score", "display_name")

    candidate_counts = candidate_qs.aggregate(
        total=Count("id"),
        high_priority=Count("id", filter=Q(priority__gte=75)),
        needs_more_evidence=Count("id", filter=Q(status=CatalogCurationCandidate.STATUS_NEEDS_MORE_EVIDENCE)),
    )
    food_counts = catalog_food_qs.aggregate(
        total=Count("id"),
        pending_review=Count("id", filter=Q(status=CatalogFood.STATUS_PENDING_REVIEW)),
        needs_more_evidence=Count("id", filter=Q(status=CatalogFood.STATUS_NEEDS_MORE_EVIDENCE)),
    )

    return {
        "candidate_counts": candidate_counts,
        "food_counts": food_counts,
        "candidates": list(candidate_qs[:limit]),
        "catalog_foods": list(catalog_food_qs[:limit]),
    }


def get_food_catalog_inventory_payload(
    *,
    query: str = "",
    status: str = "",
    source_type: str = "",
    food_group: str = "",
    solver_state: str = "",
    page: int | str = 1,
    page_size: int = 50,
) -> dict:
    """Return the complete, read-only Food Catalog observability payload."""

    normalized_query = (query or "").strip()
    normalized_status = status if status in dict(CatalogFood.STATUS_CHOICES) else ""
    normalized_source = source_type if source_type in dict(CatalogFood.SOURCE_TYPE_CHOICES) else ""
    normalized_group = (food_group or "").strip()
    normalized_solver = solver_state if solver_state in {"enabled", "disabled"} else ""

    all_foods = CatalogFood.objects.all()
    inventory_qs = (
        all_foods.select_related("created_by", "reviewed_by")
        .prefetch_related("sources", "portions", "aliases")
        .order_by("display_name", "brand_name", "country", "id")
    )

    if normalized_query:
        inventory_qs = inventory_qs.filter(
            Q(display_name__icontains=normalized_query)
            | Q(canonical_name__icontains=normalized_query)
            | Q(brand_name__icontains=normalized_query)
            | Q(food_group__icontains=normalized_query)
            | Q(food_subgroup__icontains=normalized_query)
            | Q(sources__source_name__icontains=normalized_query)
            | Q(sources__source_food_id__icontains=normalized_query)
        ).distinct()
    if normalized_status:
        inventory_qs = inventory_qs.filter(status=normalized_status)
    if normalized_source:
        inventory_qs = inventory_qs.filter(source_type=normalized_source)
    if normalized_group:
        inventory_qs = inventory_qs.filter(food_group=normalized_group)
    if normalized_solver:
        inventory_qs = inventory_qs.filter(solver_enabled=normalized_solver == "enabled")

    aggregate = all_foods.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
        solver_enabled=Count("id", filter=Q(solver_enabled=True)),
        average_quality=Avg("data_quality_score"),
        average_protein=Avg("protein_g_per_100g"),
        average_carbs=Avg("carbs_g_per_100g"),
        average_fat=Avg("fat_g_per_100g"),
        average_fiber=Avg("fiber_g_per_100g"),
        missing_group=Count("id", filter=Q(food_group="")),
        incomplete_extended_nutrition=Count(
            "id",
            filter=(
                Q(calories_kcal_per_100g__isnull=True)
                | Q(fiber_g_per_100g__isnull=True)
                | Q(sugar_g_per_100g__isnull=True)
                | Q(saturated_fat_g_per_100g__isnull=True)
                | Q(sodium_mg_per_100g__isnull=True)
            ),
            distinct=True,
        ),
        unknown_culinary_semantics=Count(
            "id",
            filter=(
                Q(preparation_state=CatalogFood.PREPARATION_UNKNOWN)
                | Q(food_form=CatalogFood.FOOD_FORM_UNKNOWN)
            ),
        ),
    )
    aggregate["without_evidence"] = all_foods.filter(sources__isnull=True).count()

    group_rows = list(
        all_foods.values("food_group")
        .annotate(
            total=Count("id"),
            published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
            solver_enabled=Count("id", filter=Q(solver_enabled=True)),
            average_quality=Avg("data_quality_score"),
        )
        .order_by("food_group")
    )
    category_coverage = _catalog_category_coverage(group_rows)
    source_breakdown = list(
        all_foods.values("source_type")
        .annotate(
            total=Count("id"),
            published=Count("id", filter=Q(status=CatalogFood.STATUS_PUBLISHED)),
            solver_enabled=Count("id", filter=Q(solver_enabled=True)),
            average_quality=Avg("data_quality_score"),
        )
        .order_by("-total", "source_type")
    )

    groups = list(
        all_foods.exclude(food_group="")
        .order_by("food_group")
        .values_list("food_group", flat=True)
        .distinct()
    )
    paginator = Paginator(inventory_qs, page_size)
    page_obj = paginator.get_page(page)

    return {
        "query": normalized_query,
        "status": normalized_status,
        "source_type": normalized_source,
        "food_group": normalized_group,
        "solver_state": normalized_solver,
        "aggregate": aggregate,
        "category_coverage": category_coverage,
        "source_breakdown": source_breakdown,
        "group_rows": group_rows,
        "status_options": CatalogFood.STATUS_CHOICES,
        "source_options": CatalogFood.SOURCE_TYPE_CHOICES,
        "group_options": groups,
        "page_obj": page_obj,
        "filtered_total": paginator.count,
        "generic_coverage": get_generic_food_coverage_payload(),
    }


def get_generic_food_coverage_payload() -> dict:
    """Reconcile the versioned planning manifest with persisted source evidence."""

    manifest = load_coverage_manifest(
        Path(__file__).resolve().parents[1]
        / "food_catalog"
        / "data"
        / "generic_food_coverage_manifest_v1.csv",
        version="gfc.v1",
    )
    mapped_targets = [target for target in manifest.targets if target.mapping_status == "mapped"]
    source_rows = CatalogFoodSource.objects.filter(
        source_food_id__in=[target.source_food_id for target in mapped_targets]
    ).select_related("catalog_food")
    foods_by_source = {
        (row.source_type, row.source_food_id): row.catalog_food
        for row in source_rows
    }

    def persisted_food(target):
        source_type = (
            CatalogFood.SOURCE_NATURAL_VERIFIED
            if target.expected_source == "internal_seed"
            else CatalogFood.SOURCE_USDA
        )
        return foods_by_source.get((source_type, target.source_food_id))

    imported_targets = [(target, persisted_food(target)) for target in mapped_targets]
    imported_targets = [(target, food) for target, food in imported_targets if food is not None]
    reviewed_statuses = {
        CatalogFood.STATUS_REVIEWED,
        CatalogFood.STATUS_VERIFIED,
        CatalogFood.STATUS_PUBLISHED,
    }
    category_rows = []
    for category, defined in manifest.counts_by_category().items():
        imported = sum(1 for target, _food in imported_targets if target.category == category)
        category_rows.append({"key": category, "defined": defined, "imported": imported})

    return {
        "version": manifest.version,
        "sha256": manifest.sha256,
        "total": manifest.total_targets,
        "source_mapped": len(mapped_targets),
        "imported": len(imported_targets),
        "reviewed": sum(1 for _target, food in imported_targets if food.status in reviewed_statuses),
        "published": sum(
            1 for _target, food in imported_targets if food.status == CatalogFood.STATUS_PUBLISHED
        ),
        "category_rows": category_rows,
    }


def get_food_catalog_import_batches_payload(*, source_type: str = "", status: str = "", limit: int = 100) -> dict:
    """Return governed dry-runs and imports without exposing source payloads."""

    normalized_source = source_type if source_type in dict(CatalogFood.SOURCE_TYPE_CHOICES) else ""
    normalized_status = status if status in dict(CatalogImportBatch.STATUS_CHOICES) else ""
    queryset = CatalogImportBatch.objects.select_related("requested_by", "dry_run_batch").order_by("-started_at", "-id")
    if normalized_source:
        queryset = queryset.filter(source_type=normalized_source)
    if normalized_status:
        queryset = queryset.filter(status=normalized_status)

    aggregate = CatalogImportBatch.objects.aggregate(
        total=Count("id"),
        dry_runs=Count("id", filter=Q(is_dry_run=True)),
        imports=Count("id", filter=Q(is_dry_run=False)),
        failed=Count(
            "id",
            filter=Q(status__in=[CatalogImportBatch.STATUS_FAILED, CatalogImportBatch.STATUS_COMPLETED_WITH_ERRORS]),
        ),
    )
    orphan_applies = CatalogImportBatch.objects.filter(is_dry_run=False, dry_run_batch__isnull=True).count()
    return {
        "source_type": normalized_source,
        "status": normalized_status,
        "aggregate": aggregate,
        "orphan_applies": orphan_applies,
        "batches": list(queryset[:limit]),
        "source_options": CatalogFood.SOURCE_TYPE_CHOICES,
        "status_options": CatalogImportBatch.STATUS_CHOICES,
    }


def _catalog_category_coverage(group_rows: list[dict]) -> list[dict]:
    family_by_alias = {
        alias.casefold(): key
        for key, _label, aliases in CATALOG_GROUP_FAMILIES
        for alias in aliases
    }
    totals = {
        key: {"key": key, "label": label, "total": 0, "published": 0, "solver_enabled": 0}
        for key, label, _aliases in CATALOG_GROUP_FAMILIES
    }
    recognized_total = 0

    for row in group_rows:
        raw_group = str(row["food_group"] or "").strip()
        family = family_by_alias.get(raw_group.casefold())
        if not family:
            continue
        recognized_total += int(row["total"] or 0)
        totals[family]["total"] += int(row["total"] or 0)
        totals[family]["published"] += int(row["published"] or 0)
        totals[family]["solver_enabled"] += int(row["solver_enabled"] or 0)

    result = list(totals.values())
    result.append({
        "key": "unmapped",
        "label": "Sin taxonomía estándar",
        "total": max(sum(int(row["total"] or 0) for row in group_rows) - recognized_total, 0),
        "published": 0,
        "solver_enabled": 0,
    })
    return result


def get_ai_operations_payload(*, query: str = "", limit: int = 25) -> dict:
    """Return actionable AI Assistant queues for OPS05.

    OPS05 deliberately focuses on existing records: recent AIUsageEvent issues,
    AI/MCP NutritionProposal records awaiting staff review, and AI credit quotas
    that may explain blocked access.
    """

    normalized_query = (query or "").strip()
    since_7d = timezone.now() - timedelta(days=7)

    event_qs = (
        AIUsageEvent.objects.select_related("user")
        .filter(status__in=AI_OPERATIONAL_STATUSES, created_at__gte=since_7d)
        .order_by("-created_at", "-id")
    )
    proposal_qs = (
        NutritionProposal.objects.select_related("created_by", "dailyplan")
        .filter(
            source__in=[NutritionProposal.SOURCE_AI, NutritionProposal.SOURCE_MCP],
            status=NutritionProposal.STATUS_PENDING_REVIEW,
        )
        .order_by("-created_at", "-id")
    )
    quota_qs = (
        AIUserCreditQuota.objects.select_related("user")
        .filter(Q(hard_blocked=True) | Q(credits_used__gte=models.F("monthly_credit_limit")))
        .order_by("-hard_blocked", "-updated_at", "user__email", "user__username")
    )

    if normalized_query:
        user_filter = (
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
        )
        event_qs = event_qs.filter(
            user_filter
            | Q(action_type__icontains=normalized_query)
            | Q(error_type__icontains=normalized_query)
            | Q(provider__icontains=normalized_query)
            | Q(model_name__icontains=normalized_query)
            | Q(conversation_id__icontains=normalized_query)
            | Q(turn_id__icontains=normalized_query)
        )
        proposal_qs = proposal_qs.filter(
            Q(created_by__email__icontains=normalized_query)
            | Q(created_by__username__icontains=normalized_query)
            | Q(title__icontains=normalized_query)
            | Q(summary__icontains=normalized_query)
            | Q(source__icontains=normalized_query)
        )
        quota_qs = quota_qs.filter(
            user_filter
            | Q(plan_code__icontains=normalized_query)
            | Q(period__icontains=normalized_query)
        )

    event_counts = event_qs.aggregate(
        total=Count("id"),
        errors=Count("id", filter=Q(status=AIUsageEvent.Status.ERROR)),
        blocked=Count("id", filter=Q(status=AIUsageEvent.Status.BLOCKED)),
    )
    proposal_counts = proposal_qs.aggregate(
        total=Count("id"),
        ai=Count("id", filter=Q(source=NutritionProposal.SOURCE_AI)),
        mcp=Count("id", filter=Q(source=NutritionProposal.SOURCE_MCP)),
    )
    quota_counts = quota_qs.aggregate(
        total=Count("id"),
        hard_blocked=Count("id", filter=Q(hard_blocked=True)),
    )

    return {
        "query": normalized_query,
        "event_counts": event_counts,
        "proposal_counts": proposal_counts,
        "quota_counts": quota_counts,
        "events": list(event_qs[:limit]),
        "proposals": list(proposal_qs[:limit]),
        "quotas": list(quota_qs[:limit]),
    }


def _build_warning_candidates(*, catalog: dict, ai: dict, accounts: dict) -> list[dict]:
    warnings: list[dict] = []

    if catalog["high_priority_candidates"]:
        warnings.append({
            "severity": "warning",
            "domain": "Food Catalog",
            "title": "Candidatos de alta prioridad",
            "value": catalog["high_priority_candidates"],
            "description": "Hay candidatos de curación con prioridad 75+ esperando revisión staff.",
        })
    elif catalog["pending_candidates"]:
        warnings.append({
            "severity": "info",
            "domain": "Food Catalog",
            "title": "Candidatos pendientes",
            "value": catalog["pending_candidates"],
            "description": "La cola ya tiene work items listos para el workflow OPS03.",
        })

    if ai.get("errors", 0):
        warnings.append({
            "severity": "warning",
            "domain": "AI Assistant",
            "title": "Errores IA recientes",
            "value": ai["errors"],
            "description": "Existen AIUsageEvent con estado error en los últimos 7 días.",
        })

    if ai.get("blocked", 0):
        warnings.append({
            "severity": "warning",
            "domain": "AI Assistant",
            "title": "Eventos IA bloqueados",
            "value": ai["blocked"],
            "description": "Hay turnos bloqueados que podrían requerir revisión de créditos, cuotas o guardrails.",
        })

    if accounts["wallets_with_reserved_credits"]:
        warnings.append({
            "severity": "watch",
            "domain": "Accounts & Credits",
            "title": "Wallets con créditos reservados",
            "value": accounts["wallets_with_reserved_credits"],
            "description": "Existen saldos reservados. OPS04 deberá distinguir reservas sanas vs. atascadas antes de liberar créditos.",
        })

    return warnings



def get_accounts_operations_payload(*, query: str = "", limit: int = 25) -> dict:
    """Return actionable Accounts & Credits queues for OPS04.

    The selector is read-only. Wallet mutations are handled by explicit services
    that append CreditLedger movements instead of editing historical entries.
    """

    normalized_query = (query or "").strip()
    wallet_qs = (
        CreditWallet.objects.select_related("user")
        .order_by("-reserved_balance", "user__email", "user__username")
    )
    if normalized_query:
        wallet_qs = wallet_qs.filter(
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
        )

    reservations_qs = _open_credit_reservations_queryset()
    if normalized_query:
        reservations_qs = reservations_qs.filter(
            Q(user__email__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(reference_type__icontains=normalized_query)
            | Q(reference_id__icontains=normalized_query)
        )

    wallet_counts = wallet_qs.aggregate(
        total=Count("id"),
        with_reserved=Count("id", filter=Q(reserved_balance__gt=0)),
        reserved_total=Sum("reserved_balance"),
    )
    wallet_counts["reserved_total"] = wallet_counts["reserved_total"] or 0
    open_reservations = reservations_qs.aggregate(
        total=Count("id"),
        reserved_total=Sum("reserved_delta"),
    )
    open_reservations["reserved_total"] = open_reservations["reserved_total"] or 0

    subscriptions = _subscriptions_by_user(wallet_qs[:limit])

    return {
        "query": normalized_query,
        "wallet_counts": wallet_counts,
        "reservation_counts": open_reservations,
        "wallets": list(wallet_qs[:limit]),
        "reservations": list(reservations_qs[:limit]),
        "subscriptions_by_user": subscriptions,
    }


def get_account_detail_payload(*, user_id: int, ledger_limit: int = 30) -> dict:
    User = get_user_model()
    user = User.objects.get(pk=user_id)
    wallet = CreditWallet.objects.select_related("user").filter(user=user).first()
    subscription = (
        AccountSubscription.objects.select_related("plan")
        .filter(user=user)
        .order_by("-created_at")
        .first()
    )
    ledger_entries = []
    reservations = []
    if wallet is not None:
        ledger_entries = list(
            CreditLedger.objects.filter(wallet=wallet)
            .select_related("user")
            .order_by("-created_at", "-id")[:ledger_limit]
        )
        reservations = list(_open_credit_reservations_queryset().filter(wallet=wallet)[:ledger_limit])
    return {
        "user": user,
        "wallet": wallet,
        "subscription": subscription,
        "ledger_entries": ledger_entries,
        "reservations": reservations,
    }


def _open_credit_reservations_queryset():
    closed_references = CreditLedger.objects.filter(
        kind__in=(CreditLedger.Kind.CONSUME, CreditLedger.Kind.RELEASE),
        reference_type__gt="",
        reference_id__gt="",
    ).values_list("reference_type", "reference_id")
    closed_pairs = {(reference_type, reference_id) for reference_type, reference_id in closed_references}

    qs = (
        CreditLedger.objects.select_related("wallet", "user")
        .filter(kind=CreditLedger.Kind.RESERVE, reserved_delta__gt=0)
        .order_by("created_at", "id")
    )
    if not closed_pairs:
        return qs

    closed_q = Q()
    for reference_type, reference_id in closed_pairs:
        closed_q |= Q(reference_type=reference_type, reference_id=reference_id)
    return qs.exclude(closed_q)


def _subscriptions_by_user(wallets) -> dict[int, AccountSubscription]:
    user_ids = [wallet.user_id for wallet in wallets]
    if not user_ids:
        return {}
    subscriptions = (
        AccountSubscription.objects.select_related("plan")
        .filter(user_id__in=user_ids)
        .order_by("user_id", "-created_at")
    )
    result: dict[int, AccountSubscription] = {}
    for subscription in subscriptions:
        result.setdefault(subscription.user_id, subscription)
    return result


def get_audit_log_payload(*, query: str = "", limit: int = 50) -> dict:
    """Return recent Admin Operations audit events for OPS06."""

    normalized_query = (query or "").strip()
    events_qs = AdminOperationAuditEvent.objects.select_related("actor").order_by("-created_at", "-id")
    if normalized_query:
        events_qs = events_qs.filter(
            Q(actor_label__icontains=normalized_query)
            | Q(action__icontains=normalized_query)
            | Q(target_app__icontains=normalized_query)
            | Q(target_model__icontains=normalized_query)
            | Q(target_id__icontains=normalized_query)
            | Q(target_label__icontains=normalized_query)
            | Q(reason__icontains=normalized_query)
        )

    total = events_qs.count()
    recent_24h = events_qs.filter(created_at__gte=timezone.now() - timedelta(days=1)).count()
    financial = events_qs.filter(target_app="accounts").count()
    ai = events_qs.filter(target_app="ai_assistant").count() + events_qs.filter(target_app="notas").count()

    return {
        "query": normalized_query,
        "events": list(events_qs[:limit]),
        "counts": {
            "total": total,
            "recent_24h": recent_24h,
            "financial": financial,
            "ai": ai,
        },
    }
