from .base import *
from .base import _env_bool

# Local development may exercise MCP without an active commercial subscription.
MCP_PRO_ENTITLEMENT_ENFORCED = _env_bool("MCP_PRO_ENTITLEMENT_ENFORCED", False)

SECRET_KEY = "dev-secret-key-local-only"

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

print("🚀 RUNNING IN DEV MODE")
