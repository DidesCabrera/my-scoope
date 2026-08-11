from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

MSOS_DATA_RELATIVE_PATH = Path("docs/company/msos/msos_data.json")


def load_msos_data() -> dict[str, Any]:
    """Load the versioned, read-only source for the MSOS view."""
    data_path = Path(settings.BASE_DIR) / MSOS_DATA_RELATIVE_PATH
    try:
        data = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ImproperlyConfigured(
            f"MSOS data could not be loaded from {MSOS_DATA_RELATIVE_PATH}."
        ) from exc
    if not isinstance(data, dict):
        raise ImproperlyConfigured("MSOS data must contain a JSON object.")
    return data
