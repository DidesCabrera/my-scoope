export class MobileApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
    readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "MobileApiError";
  }
}

export function userFacingError(error: unknown): string {
  if (error instanceof MobileApiError) {
    const messages: Record<string, string> = {
      ai_async_unavailable: "El Asistente no está disponible en este momento. Tu conversación guardada no se perderá.",
      ai_turn_rate_limited: "Has enviado varios mensajes seguidos. Espera un momento e inténtalo nuevamente.",
      assistant_turn_failed: "El turno no pudo completarse. La conversación anterior sigue guardada y puedes reintentarlo.",
      assistant_turn_pending: "El Asistente ya está procesando un mensaje en esta conversación.",
      mobile_auth_required: "Tu sesión necesita renovarse. Inicia sesión nuevamente.",
      request_validation_failed: "Revisa los datos ingresados e inténtalo nuevamente.",
      saved_comparison_not_found: "Esta comparación ya no está disponible o no pertenece a tu cuenta.",
    };
    if (messages[error.code]) return messages[error.code];
    if (error.status === 403) return "Tu cuenta no tiene permiso para realizar esta acción.";
    if (error.status === 404) return "Este contenido ya no está disponible o no pertenece a tu cuenta.";
    if (error.status === 409) return "El contenido cambió mientras lo revisabas. Actualiza la pantalla e inténtalo nuevamente.";
    if (error.status === 422) return "No pudimos validar esta solicitud. Revisa los datos e inténtalo nuevamente.";
    if (error.status === 429) return "Has realizado varias solicitudes seguidas. Espera un momento e inténtalo nuevamente.";
    if (error.status === 503) return "Este servicio no está disponible en este momento. Inténtalo más tarde.";
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "No pudimos completar la acción. Inténtalo nuevamente.";
}
