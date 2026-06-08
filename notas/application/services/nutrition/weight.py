from notas.domain.models import WeightLog


DEFAULT_CURRENT_WEIGHT_KG = 75
_WEIGHT_LOG_NOT_QUERIED = object()


def get_current_weight_log(user):
    cached_log = getattr(
        user,
        "_myscoope_current_weight_log",
        _WEIGHT_LOG_NOT_QUERIED,
    )

    if cached_log is not _WEIGHT_LOG_NOT_QUERIED:
        return cached_log

    last = user.weight_logs.first()
    setattr(user, "_myscoope_current_weight_log", last)
    return last


def get_current_weight(user):
    last = get_current_weight_log(user)
    return last.weight_kg if last else DEFAULT_CURRENT_WEIGHT_KG
