from __future__ import annotations

import re

from django.conf import settings

IOS_BUNDLE_ID = "com.myscoope.app"
ANDROID_PACKAGE = "com.myscoope.app"
TEAM_ID_PATTERN = re.compile(r"^[A-Z0-9]{10}$")
FINGERPRINT_PATTERN = re.compile(r"^(?:[0-9A-F]{2}:){31}[0-9A-F]{2}$")


def apple_app_site_association_payload() -> dict | None:
    team_id = str(getattr(settings, "MYSCOOPE_APPLE_TEAM_ID", "")).strip().upper()
    if not TEAM_ID_PATTERN.fullmatch(team_id):
        return None
    return {
        "applinks": {
            "apps": [],
            "details": [
                {
                    "appID": f"{team_id}.{IOS_BUNDLE_ID}",
                    "paths": ["/s/*"],
                }
            ],
        }
    }


def android_asset_links_payload() -> list[dict] | None:
    fingerprints = [
        str(value).strip().upper()
        for value in getattr(settings, "MYSCOOPE_ANDROID_SHA256_CERT_FINGERPRINTS", [])
        if str(value).strip()
    ]
    if not fingerprints or any(not FINGERPRINT_PATTERN.fullmatch(value) for value in fingerprints):
        return None
    return [
        {
            "relation": ["delegate_permission/common.handle_all_urls"],
            "target": {
                "namespace": "android_app",
                "package_name": ANDROID_PACKAGE,
                "sha256_cert_fingerprints": fingerprints,
            },
        }
    ]
