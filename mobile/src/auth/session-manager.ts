import { MobileApiError } from "@/api/errors";
import { invalidateCalendarMonthCaches } from "@/components/calendarization/calendar-month-cache";
import type {
  ApiEnvelope,
  OAuthErrorResponse,
  OAuthTokenResponse,
  SessionData,
} from "@/api/types";
import { normalizeDiagnosticPath, sanitizeRequestId } from "@/observability/sanitize";

export type StoredTokenSet = {
  accessToken: string;
  refreshToken: string;
  accessExpiresAt: number;
  refreshExpiresAt: number;
  scope: string;
  deviceSessionId: string;
};

export type TokenStorage = {
  get(): Promise<StoredTokenSet | null>;
  set(tokens: StoredTokenSet): Promise<void>;
  clear(): Promise<void>;
};

export type DeviceIdentity = {
  id: string;
  name: string;
  platform: "ios" | "android" | "web";
};

type FetchLike = typeof fetch;

export type MobileRequestMetric = {
  cache: "deduplicated" | "fresh" | "network" | "revalidated";
  durationMs: number;
  errorCode: string | null;
  method: string;
  outcome: "api_error" | "invalid_response" | "network_error" | "success";
  path: string;
  requestId: string | null;
  responseBytes: number | null;
  status: number;
};

type CachedResponse = {
  data: unknown;
  etag: string | null;
  storedAt: number;
};

export type SessionManagerConfig = {
  apiBaseUrl: string;
  oauthClientId: string;
  oauthRedirectUri: string;
  oauthTokenEndpoint: string;
};

const REFRESH_SKEW_MS = 60_000;

export class MobileSessionManager {
  private tokens: StoredTokenSet | null = null;
  private readonly responseCache = new Map<string, CachedResponse>();
  private readonly inFlightReads = new Map<string, Promise<unknown>>();
  private cacheGeneration = 0;
  private sessionGeneration = 0;
  private storageMutation: Promise<void> = Promise.resolve();
  private refreshPromise: Promise<void> | null = null;
  private metricObserver: ((metric: MobileRequestMetric) => void) | null = null;

  constructor(
    private readonly config: SessionManagerConfig,
    private readonly storage: TokenStorage,
    private readonly getDeviceIdentity: () => Promise<DeviceIdentity>,
    private readonly fetchImpl: FetchLike = fetch,
    private readonly now: () => number = Date.now,
  ) {}

  setRequestMetricObserver(observer: (metric: MobileRequestMetric) => void): void {
    this.metricObserver = observer;
  }
  get hasCredentials(): boolean { return this.tokens !== null; }

  async restore(): Promise<SessionData | null> {
    const sessionGeneration = this.sessionGeneration;
    const restoredTokens = await this.storage.get();
    if (sessionGeneration !== this.sessionGeneration) return null;
    this.tokens = restoredTokens;
    if (!this.tokens || this.tokens.refreshExpiresAt <= this.now()) {
      await this.clear();
      return null;
    }

    try {
      if (this.accessNeedsRefresh()) {
        await this.refresh();
      }
      return await this.request<SessionData>("/api/v1/session");
    } catch (error) {
      if (error instanceof MobileApiError && [400, 401, 403].includes(error.status)) {
        if (sessionGeneration === this.sessionGeneration) await this.clear();
        return null;
      }
      // A network/server outage must not destroy the rotating credentials.
      throw error;
    }
  }

  async exchangeAuthorizationCode(code: string, codeVerifier: string): Promise<SessionData> {
    const sessionGeneration = ++this.sessionGeneration;
    invalidateCalendarMonthCaches();
    this.cacheGeneration += 1;
    this.responseCache.clear();
    this.inFlightReads.clear();
    this.tokens = null;
    await this.persist(null);
    const device = await this.getDeviceIdentity();
    const body = new URLSearchParams({
      grant_type: "authorization_code",
      client_id: this.config.oauthClientId,
      code,
      redirect_uri: this.config.oauthRedirectUri,
      code_verifier: codeVerifier,
      device_id: device.id,
      device_name: device.name,
      platform: device.platform,
    });
    const response = await this.fetchImpl(this.config.oauthTokenEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });
    await this.acceptTokenResponse(response, sessionGeneration);
    return this.request<SessionData>("/api/v1/session");
  }

  async request<T>(path: string, init: RequestInit = {}, canRetry = true): Promise<T> {
    if (!this.tokens) {
      throw new MobileApiError("Inicia sesión para continuar.", "mobile_auth_required", 401);
    }
    if (this.accessNeedsRefresh()) {
      await this.refresh();
    }

    const method = (init.method ?? "GET").toUpperCase();
    const cacheKey = `${method}:${path}`;
    if (method === "GET") {
      if (init.cache === "no-store" || init.cache === "reload") {
        return this.performRequest<T>(path, init, canRetry, null, -1);
      }
      const cached = this.responseCache.get(cacheKey);
      if (cached && this.now() - cached.storedAt <= this.cacheTtl(path)) {
        this.reportMetric({ cache: "fresh", durationMs: 0, errorCode: null, method, outcome: "success", path, requestId: null, responseBytes: 0, status: 200 });
        return cached.data as T;
      }
      const existing = this.inFlightReads.get(cacheKey);
      if (existing) {
        this.reportMetric({ cache: "deduplicated", durationMs: 0, errorCode: null, method, outcome: "success", path, requestId: null, responseBytes: 0, status: 200 });
        return existing as Promise<T>;
      }
      const request = this.performRequest<T>(path, init, canRetry, cached ?? null, this.cacheGeneration);
      this.inFlightReads.set(cacheKey, request);
      try {
        return await request;
      } finally {
        if (this.inFlightReads.get(cacheKey) === request) this.inFlightReads.delete(cacheKey);
      }
    }

    const result = await this.performRequest<T>(path, init, canRetry, null);
    this.invalidateAfterMutation(path);
    return result;
  }

  private async performRequest<T>(
    path: string,
    init: RequestInit,
    canRetry: boolean,
    cached: CachedResponse | null,
    cacheGeneration = this.cacheGeneration,
  ): Promise<T> {
    const startedAt = this.now();
    const method = (init.method ?? "GET").toUpperCase();
    const tokens = this.tokens;
    const sessionGeneration = this.sessionGeneration;
    if (!tokens) {
      throw new MobileApiError("Inicia sesión para continuar.", "mobile_auth_required", 401);
    }
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${tokens.accessToken}`);
    if (cached?.etag) headers.set("If-None-Match", cached.etag);
    if (init.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    let response: Response;
    try {
      response = await this.fetchImpl(`${this.config.apiBaseUrl}${path}`, {
        ...init,
        headers,
      });
    } catch (error) {
      this.reportMetric({ cache: "network", durationMs: this.now() - startedAt, errorCode: null, method, outcome: "network_error", path, requestId: null, responseBytes: null, status: 0 });
      if (sessionGeneration !== this.sessionGeneration) {
        throw new MobileApiError("La sesión cambió durante la solicitud.", "mobile_session_changed", 401);
      }
      throw error;
    }
    if (sessionGeneration !== this.sessionGeneration) {
      throw new MobileApiError("La sesión cambió durante la solicitud.", "mobile_session_changed", 401);
    }

    if (response.status === 401 && canRetry) {
      await this.refresh();
      return this.performRequest<T>(path, init, false, cached, cacheGeneration);
    }
    if (response.status === 304 && cached) {
      cached.storedAt = this.now();
      this.reportMetric({ cache: "revalidated", durationMs: this.now() - startedAt, errorCode: null, method, outcome: "success", path, requestId: this.responseRequestId(response), responseBytes: 0, status: 304 });
      return cached.data as T;
    }
    const contentType = response.headers.get("Content-Type")?.toLowerCase() ?? "";
    if (!contentType.includes("application/json")) {
      const contentLength = Number(response.headers.get("Content-Length"));
      const requestId = this.responseRequestId(response);
      this.reportMetric({
        cache: "network",
        durationMs: this.now() - startedAt,
        errorCode: "mobile_api_invalid_response",
        method,
        outcome: "invalid_response",
        path,
        requestId,
        responseBytes: Number.isFinite(contentLength) ? contentLength : null,
        status: response.status,
      });
      throw new MobileApiError(
        response.status === 404
          ? "Esta función todavía no está disponible en el servidor seleccionado."
          : "El servidor devolvió una respuesta inesperada. Inténtalo nuevamente.",
        "mobile_api_invalid_response",
        response.status,
        {},
        requestId,
      );
    }
    const responseText = await response.text();
    const responseBytes = new TextEncoder().encode(responseText).length;
    let payload: ApiEnvelope<T>;
    try {
      payload = JSON.parse(responseText) as ApiEnvelope<T>;
    } catch {
      const requestId = this.responseRequestId(response);
      this.reportMetric({ cache: "network", durationMs: this.now() - startedAt, errorCode: "mobile_api_invalid_json", method, outcome: "invalid_response", path, requestId, responseBytes, status: response.status });
      throw new MobileApiError(
        "El servidor devolvió una respuesta inesperada. Inténtalo nuevamente.",
        "mobile_api_invalid_response",
        response.status,
        {},
        requestId,
      );
    }
    if (sessionGeneration !== this.sessionGeneration) {
      throw new MobileApiError("La sesión cambió durante la solicitud.", "mobile_session_changed", 401);
    }
    const requestId = this.responseRequestId(response);
    if (!response.ok || !payload.ok) {
      const detail = payload.ok
        ? { code: "mobile_api_error", message: "La solicitud no pudo completarse.", details: {} }
        : payload.error;
      this.reportMetric({ cache: "network", durationMs: this.now() - startedAt, errorCode: detail.code, method, outcome: "api_error", path, requestId, responseBytes, status: response.status });
      throw new MobileApiError(detail.message, detail.code, response.status, detail.details, requestId);
    }
    this.reportMetric({ cache: "network", durationMs: this.now() - startedAt, errorCode: null, method, outcome: "success", path, requestId, responseBytes, status: response.status });
    if (method === "GET" && cacheGeneration === this.cacheGeneration) {
      this.responseCache.set(`${method}:${path}`, {
        data: payload.data,
        etag: response.headers.get("ETag"),
        storedAt: this.now(),
      });
    }
    return payload.data;
  }

  async signOut(): Promise<void> {
    const sessionId = this.tokens?.deviceSessionId;
    if (sessionId) {
      try {
        await this.request(`/api/v1/sessions/${sessionId}`, { method: "DELETE" });
      } catch {
        // Local sign-out must still succeed when the network is unavailable.
      }
    }
    await this.clear();
  }

  async clear(): Promise<void> {
    this.sessionGeneration += 1;
    invalidateCalendarMonthCaches();
    this.cacheGeneration += 1;
    this.tokens = null;
    this.responseCache.clear();
    this.inFlightReads.clear();
    await this.persist(null);
  }

  private persist(tokens: StoredTokenSet | null): Promise<void> {
    const task = this.storageMutation.catch(() => undefined).then(() => tokens ? this.storage.set(tokens) : this.storage.clear());
    this.storageMutation = task;
    return task;
  }

  private cacheTtl(path: string): number {
    if (path === "/api/v1/home" || path === "/api/v1/home/summary") return 20_000;
    if (path === "/api/v1/session" || path === "/api/v1/me") return 60_000;
    if (path.startsWith("/api/v1/library/")) return 20_000;
    return 10_000;
  }

  private invalidateAfterMutation(path: string): void {
    this.cacheGeneration += 1;
    const changesCalendar = path.startsWith("/api/v1/calendar/")
      || path.startsWith("/api/v1/program/")
      || path.startsWith("/api/v1/today/")
      || path.startsWith("/api/v1/days/");
    if (changesCalendar) invalidateCalendarMonthCaches();
    const affectedPrefixes = path.startsWith("/api/v1/calendar/")
      ? ["/api/v1/home", "/api/v1/today", "/api/v1/program/", "/api/v1/calendar"]
      : path.includes("/library/")
      ? ["/api/v1/home", "/api/v1/library/", "/api/v1/today", "/api/v1/program/"]
      : path.includes("/weights")
        ? ["/api/v1/home", "/api/v1/weights", "/api/v1/me"]
        : path.includes("/proposals") || path.includes("/ai/")
          ? ["/api/v1/home", "/api/v1/proposals", "/api/v1/ai/"]
          : path.includes("/today") || path.includes("/program/") || path.includes("/days/")
            ? ["/api/v1/home", "/api/v1/today", "/api/v1/program/", "/api/v1/calendar", "/api/v1/days/"]
            : ["/api/v1/"];
    const isAffected = (key: string) => affectedPrefixes.some(
      (prefix) => key.slice(key.indexOf(":") + 1).startsWith(prefix),
    );
    for (const key of this.responseCache.keys()) {
      if (isAffected(key)) this.responseCache.delete(key);
    }
    for (const key of this.inFlightReads.keys()) {
      if (isAffected(key)) this.inFlightReads.delete(key);
    }
  }

  private reportMetric(metric: MobileRequestMetric): void {
    this.metricObserver?.({
      ...metric,
      path: normalizeDiagnosticPath(metric.path),
    });
  }

  private responseRequestId(response: Response): string | null {
    return sanitizeRequestId(response.headers.get("Rndr-Id") ?? response.headers.get("X-Request-ID"));
  }

  private accessNeedsRefresh(): boolean {
    return !this.tokens || this.tokens.accessExpiresAt <= this.now() + REFRESH_SKEW_MS;
  }

  private async refresh(): Promise<void> {
    if (this.refreshPromise) return this.refreshPromise;
    const task = this.performRefresh();
    this.refreshPromise = task;
    try {
      await task;
    } finally {
      if (this.refreshPromise === task) this.refreshPromise = null;
    }
  }

  private async performRefresh(): Promise<void> {
    const sessionGeneration = this.sessionGeneration;
    if (!this.tokens || this.tokens.refreshExpiresAt <= this.now()) {
      await this.clear();
      throw new MobileApiError("Tu sesión expiró. Inicia sesión nuevamente.", "mobile_session_expired", 401);
    }
    try {
      const response = await this.fetchImpl(this.config.oauthTokenEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          grant_type: "refresh_token",
          client_id: this.config.oauthClientId,
          refresh_token: this.tokens.refreshToken,
        }).toString(),
      });
      await this.acceptTokenResponse(response, sessionGeneration);
    } catch (error) {
      if (sessionGeneration === this.sessionGeneration && error instanceof MobileApiError && [400, 401].includes(error.status)) {
        await this.clear();
      }
      throw error;
    }
  }

  private async acceptTokenResponse(response: Response, sessionGeneration: number): Promise<void> {
    const payload = (await response.json()) as OAuthTokenResponse | OAuthErrorResponse;
    if (sessionGeneration !== this.sessionGeneration) {
      throw new MobileApiError("La sesión cambió durante la solicitud.", "mobile_session_changed", 401);
    }
    if (!response.ok || !("access_token" in payload)) {
      const error = payload as OAuthErrorResponse;
      throw new MobileApiError(
        error.error_description ?? "No pudimos completar el inicio de sesión.",
        error.details?.code ?? error.error ?? "oauth_exchange_failed",
        response.status,
        error.details ?? {},
      );
    }
    const issuedAt = this.now();
    this.tokens = {
      accessToken: payload.access_token,
      refreshToken: payload.refresh_token,
      accessExpiresAt: issuedAt + payload.expires_in * 1000,
      refreshExpiresAt: issuedAt + payload.refresh_expires_in * 1000,
      scope: payload.scope,
      deviceSessionId: payload.device_session_id,
    };
    await this.persist(this.tokens);
    if (sessionGeneration !== this.sessionGeneration) {
      throw new MobileApiError("La sesión cambió durante la solicitud.", "mobile_session_changed", 401);
    }
  }
}
