from __future__ import annotations


ROUTE_DOMAIN_PREFIXES = (
    ("/ai/", "assistant"),
    ("/program/", "calendarization"),
    ("/today", "calendarization"),
    ("/days/", "calendarization"),
    ("/notifications/", "calendarization"),
    ("/weights", "calendarization"),
    ("/proposals", "proposals"),
    ("/comparisons", "comparisons"),
    ("/library", "libraries"),
    ("/foods", "food_catalog"),
    ("/food-picker-options", "food_catalog"),
    ("/subscriptions", "billing"),
    ("/entitlements", "billing"),
    ("/account", "accounts"),
    ("/onboarding", "accounts"),
    ("/me", "accounts"),
    ("/sessions", "identity"),
    ("/session", "identity"),
    ("/health", "platform"),
)


def route_domain(path: str) -> str | None:
    return next((domain for prefix, domain in ROUTE_DOMAIN_PREFIXES if path.startswith(prefix)), None)
