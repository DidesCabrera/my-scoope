import { MobileApiError, userFacingError } from "../api/errors";

export function storeBillingError(error: unknown, action: "restore" | "purchase" | "verify" = "purchase", store: "Apple" | "Google Play" = "Apple"): string {
  if (error instanceof MobileApiError) return userFacingError(error);
  if (action === "restore") return `No pudimos conectarnos con ${store}. Revisa tu conexión e inténtalo nuevamente.`;
  if (action === "verify") return "No pudimos verificar la compra en este momento. Usa Restaurar compras para reintentarlo.";
  return "No pudimos completar la operación con la tienda. Revisa tu conexión e inténtalo nuevamente.";
}
