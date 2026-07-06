from accounts.services.entitlements import resolve_account_entitlements


def get_capabilities(user):
    if not user or not user.is_authenticated:
        return None

    if not hasattr(user, "profile"):
        return None

    return Capabilities(user)


class Capabilities:
    def __init__(self, user):
        self.user = user
        self.profile = user.profile
        self.plan = self.profile.plan  # legacy compatibility during ACC migration
        self.role = self.profile.role
        self.account_entitlements = resolve_account_entitlements(user)

    # -----------------
    # CREATION
    # -----------------

    def can_create_food(self):
        return self._enabled("can_create_food")

    def can_create_meal(self):
        return self._enabled("can_create_meal")

    def can_create_dailyplan(self):
        return self._enabled("can_create_dailyplan")

    def can_create_program(self):
        return self._enabled("can_create_program")

    # -----------------
    # VISIBILITY
    # -----------------

    def can_publish(self):
        return self._enabled("can_publish")

    # -----------------
    # FORK / COPY
    # -----------------

    def can_fork(self):
        return self._enabled("can_fork", default=True)

    def can_copy(self):
        return self._enabled("can_copy")

    # -----------------
    # LIMITS
    # -----------------

    def max_program_duration_days(self):
        return self._limit("max_program_duration_days")

    def max_active_subscriptions(self):
        return self._limit("max_active_subscriptions")

    # -----------------
    # EDITING
    # -----------------

    def can_edit_own_content(self):
        return True

    def can_replace_meal(self):
        return True

    def can_access_distribution_settings(self):
        return self.can_publish() or self.can_copy()

    # -----------------
    # ROLE OVERRIDES
    # -----------------

    def is_admin(self):
        return self.role == "admin"

    # -----------------
    # INTERNALS
    # -----------------

    def _enabled(self, key, *, default=False):
        if self.account_entitlements is not None:
            return self.account_entitlements.enabled(key, default=default)
        return bool(self.plan and getattr(self.plan, key, default))

    def _limit(self, key):
        if self.account_entitlements is not None:
            return self.account_entitlements.limit(key)
        if self.plan is None:
            return None
        return getattr(self.plan, key, None)
