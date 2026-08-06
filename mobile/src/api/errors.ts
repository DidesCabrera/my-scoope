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
    return error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "No pudimos completar la acción. Inténtalo nuevamente.";
}
