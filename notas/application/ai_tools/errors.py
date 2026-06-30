from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404

from notas.application.ai_tools.results import (
    AIToolResult,
    tool_error,
)


def map_exception_to_tool_error(exc: Exception) -> AIToolResult:
    """
    Convierte excepciones conocidas en errores estables para tools internas.

    Esta función evita exponer excepciones crudas de Django hacia futuras
    capas API/MCP/IA.
    """
    if isinstance(exc, (Http404, ObjectDoesNotExist)):
        return tool_error(
            code="not_found",
            message="The requested resource was not found or is not available for this user.",
        )

    if isinstance(exc, ValueError):
        return tool_error(
            code=str(exc),
            message="The requested operation is not valid.",
        )

    return tool_error(
        code="unexpected_error",
        message="An unexpected error occurred while running the AI tool.",
    )