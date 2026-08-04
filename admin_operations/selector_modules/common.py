from __future__ import annotations


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





__all__ = []
