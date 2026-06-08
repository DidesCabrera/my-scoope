from notas.domain.models import WeightLog


def get_current_weight_log(user):
    cached_log = getattr(user, "_myscoope_current_weight_log", None)

    if cached_log is not None:
        return cached_log

    last = user.weight_logs.first()
    setattr(user, "_myscoope_current_weight_log", last)
    return last


def get_current_weight(user):
    last = get_current_weight_log(user)
    return last.weight_kg if last else None
