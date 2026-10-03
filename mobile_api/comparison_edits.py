from notas.application.services.commands.saved_comparison_commands import rename_saved_comparison
from notas.domain.models import SavedComparison


def rename_comparison(user, *, comparison_id: int, name: str):
    comparison = SavedComparison.objects.filter(pk=comparison_id, owner=user).first()
    if comparison is None:
        raise ValueError("saved_comparison_not_found")
    return rename_saved_comparison(comparison=comparison, name=name).comparison
