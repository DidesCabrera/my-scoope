"""Compatibility facade for domain-owned Admin Operations services.

New code should import the relevant module under ``service_modules``. Existing
callers keep their stable import surface while the application layer is decomposed.
"""

from admin_operations.service_modules.accounts import *  # noqa: F403
from admin_operations.service_modules.ai_assistant import *  # noqa: F403
from admin_operations.service_modules.audit import *  # noqa: F403
from admin_operations.service_modules.common import *  # noqa: F403
from admin_operations.service_modules.food_catalog import *  # noqa: F403
from admin_operations.service_modules.overview import *  # noqa: F403
