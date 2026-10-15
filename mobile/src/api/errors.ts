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

const connectionMessage = "No pudimos conectarnos. Revisa tu conexión e inténtalo nuevamente.";
const genericMessage = "No pudimos completar la acción. Inténtalo nuevamente.";

/** Expo can wrap fetch failures in Error, nativeError or cause. Read only the
 * bounded diagnostic fields; never stringify an arbitrary native exception. */
export function isConnectionError(error: unknown): boolean {
  const seen = new Set<unknown>();
  const pending: unknown[] = [error];
  for (let index = 0; index < pending.length && index < 12; index += 1) {
    const item = pending[index];
    if (seen.has(item)) continue;
    seen.add(item);
    if (typeof item === "string" && /fetch failed|failed to fetch|network request failed|networkerror|network_error|e_network|err_network|nsurlerrordomain|internet|offline|sin conexi[oó]n|conexi[oó]n.*(?:desactivada|perdida|interrumpida)/i.test(item)) return true;
    if (item && typeof item === "object") {
      const fields = item as Record<string, unknown>;
      if (item instanceof MobileApiError && item.status === 0) return true;
      pending.push(fields.message, fields.code, fields.cause, fields.nativeError);
    }
  }
  return false;
}

function safeMessage(message: string): string {
  return !message || message.length > 300 || /[\r\n]|Exception|NS\w*Domain|ExpoModulesCore|ConcurrentFunctionDefinition|Promise\.swift|\bSwift\b|\.(?:swift|kt|java):\d|(?:Type|Syntax|Reference)Error|stack\s?trace|\bat\s+\S+\s*\(/i.test(message)
    ? genericMessage : message;
}

export function userFacingError(error: unknown): string {
  if (isConnectionError(error)) return connectionMessage;
  if (error instanceof MobileApiError) {
    const messages: Record<string, string> = {
      ai_async_unavailable: "El Asistente no está disponible en este momento. Tu conversación guardada no se perderá.",
      ai_turn_rate_limited: "Has enviado varios mensajes seguidos. Espera un momento e inténtalo nuevamente.",
      apple_reconciliation_rate_limited: "Espera un momento antes de consultar nuevamente tu suscripción con Apple.",
      apple_transaction_mismatch: "La transacción no corresponde a esta cuenta, producto o entorno de la tienda.",
      apple_transaction_invalid: "No pudimos verificar el comprobante de Apple. Usa Restaurar compras para recuperarlo.",
      apple_billing_unavailable: "No pudimos consultar Apple en este momento. Tu compra sigue pendiente de verificación; no vuelvas a comprar.",
      assistant_turn_failed: "El turno no pudo completarse. La conversación anterior sigue guardada y puedes reintentarlo.",
      assistant_turn_pending: "El Asistente ya está procesando un mensaje en esta conversación.",
      account_username_invalid: "Usa sólo letras, números y los caracteres @, punto, +, guion o guion bajo.",
      account_username_required: "Ingresa un nombre de usuario antes de guardar.",
      account_username_too_long: "El nombre de usuario es demasiado largo.",
      account_username_unavailable: "Ese nombre de usuario ya está en uso. Prueba con otro.",
      library_delete_blocked: "Este contenido no se puede eliminar en su estado actual.",
      library_name_required: "Ingresa un nombre antes de guardar.",
      library_name_too_long: "El nombre es demasiado largo.",
      library_share_email_invalid: "Ingresa un correo válido para compartir.",
      library_share_subject_too_long: "El asunto es demasiado largo.",
      mobile_auth_required: "Tu sesión necesita renovarse. Inicia sesión nuevamente.",
      mobile_api_invalid_response: safeMessage(error.message),
      nutrition_label_could_not_resolve: "No pudimos leer esta etiqueta con suficiente seguridad. Prueba otra foto.",
      nutrition_label_insufficient_credits: "No tienes créditos suficientes para digitalizar esta etiqueta. Puedes ingresarla manualmente.",
      food_label_volume_weight_required: "Indica cuánto pesan 100 ml antes de guardar este alimento.",
      nutrition_label_scan_rate_limited: "Has digitalizado varias etiquetas seguidas. Espera un momento o ingrésala manualmente.",
      request_validation_failed: "Revisa los datos ingresados e inténtalo nuevamente.",
      saved_comparison_not_found: "Esta comparación ya no está disponible o no pertenece a tu cuenta.",
      share_resource_already_claimed: "Este enlace ya fue agregado por otra persona.",
      share_claims_disabled: "Este enlace es sólo de lectura.",
      share_self_claim_not_allowed: "Este contenido ya pertenece a tu biblioteca.",
      share_self_recipient_not_allowed: "No puedes compartir contenido contigo mismo.",
      share_resource_expired: "Este enlace compartido venció.",
      share_resource_not_active: "Este enlace compartido fue revocado.",
      sharing_inbox_item_not_found: "Este elemento ya no está disponible en tu Inbox.",
    };
    if (messages[error.code]) return messages[error.code];
    if (error.status === 403) return "Tu cuenta no tiene permiso para realizar esta acción.";
    if (error.status === 404) return "Este contenido ya no está disponible o no pertenece a tu cuenta.";
    if (error.status === 409) return "El contenido cambió mientras lo revisabas. Actualiza la pantalla e inténtalo nuevamente.";
    if (error.status === 422) return "No pudimos validar esta solicitud. Revisa los datos e inténtalo nuevamente.";
    if (error.status === 429) return "Has realizado varias solicitudes seguidas. Espera un momento e inténtalo nuevamente.";
    if (error.status === 503) return "Este servicio no está disponible en este momento. Inténtalo más tarde.";
    return error.status >= 500 ? genericMessage : safeMessage(error.message);
  }
  if (error instanceof Error && error.message) {
    return safeMessage(error.message);
  }
  return genericMessage;
}
