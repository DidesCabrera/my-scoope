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
      library_delete_blocked: "Este contenido no se puede eliminar en su estado actual.",
      library_name_required: "Ingresa un nombre antes de guardar.",
      library_name_too_long: "El nombre es demasiado largo.",
      library_share_email_invalid: "Ingresa un correo válido para compartir.",
      library_share_subject_too_long: "El asunto es demasiado largo.",
      mobile_auth_required: "Tu sesión necesita renovarse. Inicia sesión nuevamente.",
      nutrition_label_could_not_resolve: "No pudimos leer esta etiqueta con suficiente seguridad. Prueba otra foto.",
      nutrition_label_insufficient_credits: "No tienes créditos suficientes para digitalizar esta etiqueta. Puedes ingresarla manualmente.",
      nutrition_label_scan_rate_limited: "Has digitalizado varias etiquetas seguidas. Espera un momento o ingrésala manualmente.",
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
