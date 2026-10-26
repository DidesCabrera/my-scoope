from __future__ import annotations

ROUTE_DOMAIN_PREFIXES = (
    ("/ai/", "assistant"),
    ("/home", "home"),
    ("/calendar", "calendarization"),
    ("/program/", "calendarization"),
    ("/today", "calendarization"),
    ("/days/", "calendarization"),
    ("/notifications/", "calendarization"),
    ("/weights", "calendarization"),
    ("/proposals", "proposals"),
    ("/comparisons", "comparisons"),
    ("/shares", "sharing"),
    ("/explore", "libraries"),
    ("/library", "libraries"),
    ("/foods", "food_catalog"),
    ("/food-picker-options", "food_catalog"),
    ("/subscriptions", "billing"),
    ("/credit-packs", "billing"),
    ("/entitlements", "billing"),
    ("/account", "accounts"),
    ("/learning", "learning"),
    ("/onboarding", "accounts"),
    ("/personal-records", "accounts"),
    ("/me", "accounts"),
    ("/sessions", "identity"),
    ("/session", "identity"),
    ("/health", "platform"),
)


def route_domain(path: str) -> str | None:
    if path == "/notifications" or path.startswith("/notifications/{kind}/"):
        return "notification_center"
    return next((domain for prefix, domain in ROUTE_DOMAIN_PREFIXES if path.startswith(prefix)), None)
