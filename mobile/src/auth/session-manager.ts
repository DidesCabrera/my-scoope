import { MobileApiError } from "@/api/errors";
import type {
  ApiEnvelope,
  OAuthErrorResponse,
  OAuthTokenResponse,
  SessionData,
} from "@/api/types";

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
  method: string;
  path: string;
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

  async restore(): Promise<SessionData | null> {
    this.tokens = await this.storage.get();
    if (!this.tokens || this.tokens.refreshExpiresAt <= this.now()) {
      await this.clear();
      return null;
    }

    try {
      if (this.accessNeedsRefresh()) {
        await this.refresh();
      }
      return await this.request<SessionData>("/api/v1/session");
    } catch {
      await this.clear();
      return null;
    }
  }

  async exchangeAuthorizationCode(code: string, codeVerifier: string): Promise<SessionData> {
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
    await this.acceptTokenResponse(response);
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
      const cached = this.responseCache.get(cacheKey);
      if (cached && this.now() - cached.storedAt <= this.cacheTtl(path)) {
        this.reportMetric({ cache: "fresh", durationMs: 0, method, path, responseBytes: 0, status: 200 });
        return cached.data as T;
      }
      const existing = this.inFlightReads.get(cacheKey);
      if (existing) {
        this.reportMetric({ cache: "deduplicated", durationMs: 0, method, path, responseBytes: 0, status: 200 });
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
      this.reportMetric({ cache: "network", durationMs: this.now() - startedAt, method, path, responseBytes: null, status: 0 });
      throw error;
    }

    if (response.status === 401 && canRetry) {
      await this.refresh();
      return this.performRequest<T>(path, init, false, cached, cacheGeneration);
    }
    if (response.status === 304 && cached) {
      cached.storedAt = this.now();
      this.reportMetric({ cache: "revalidated", durationMs: this.now() - startedAt, method, path, responseBytes: 0, status: 304 });
      return cached.data as T;
    }
    const contentType = response.headers.get("Content-Type")?.toLowerCase() ?? "";
    if (!contentType.includes("application/json")) {
      const contentLength = Number(response.headers.get("Content-Length"));
      this.reportMetric({
        cache: "network",
        durationMs: this.now() - startedAt,
        method,
        path,
        responseBytes: Number.isFinite(contentLength) ? contentLength : null,
        status: response.status,
      });
      throw new MobileApiError(
        response.status === 404
          ? "Esta función todavía no está disponible en el servidor seleccionado."
          : "El servidor devolvió una respuesta inesperada. Inténtalo nuevamente.",
        "mobile_api_invalid_response",
        response.status,
      );
    }
    const responseText = await response.text();
    const responseBytes = new TextEncoder().encode(responseText).length;
    const payload = JSON.parse(responseText) as ApiEnvelope<T>;
    this.reportMetric({ cache: "network", durationMs: this.now() - startedAt, method, path, responseBytes, status: response.status });
    if (!response.ok || !payload.ok) {
      const detail = payload.ok
        ? { code: "mobile_api_error", message: "La solicitud no pudo completarse.", details: {} }
        : payload.error;
      throw new MobileApiError(detail.message, detail.code, response.status, detail.details);
    }
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
    this.tokens = null;
    this.responseCache.clear();
    this.inFlightReads.clear();
    await this.storage.clear();
  }

  private cacheTtl(path: string): number {
    if (path === "/api/v1/home") return 20_000;
    if (path === "/api/v1/session" || path === "/api/v1/me") return 60_000;
    if (path.startsWith("/api/v1/library/")) return 20_000;
    return 10_000;
  }

  private invalidateAfterMutation(path: string): void {
    this.cacheGeneration += 1;
    const affectedPrefixes = path.includes("/library/")
      ? ["/api/v1/home", "/api/v1/library/", "/api/v1/today", "/api/v1/program/"]
      : path.includes("/weights")
        ? ["/api/v1/home", "/api/v1/weights", "/api/v1/me"]
        : path.includes("/proposals") || path.includes("/ai/")
          ? ["/api/v1/home", "/api/v1/proposals", "/api/v1/ai/"]
          : path.includes("/today") || path.includes("/program/") || path.includes("/days/")
            ? ["/api/v1/home", "/api/v1/today", "/api/v1/program/", "/api/v1/days/"]
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
      path: metric.path.replace(
        /\/(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27,}|[A-Za-z0-9_-]{20,})(?=\/|\?|$)/gi,
        "/:id",
      ),
    });
  }

  private accessNeedsRefresh(): boolean {
    return !this.tokens || this.tokens.accessExpiresAt <= this.now() + REFRESH_SKEW_MS;
  }

  private async refresh(): Promise<void> {
    if (this.refreshPromise) return this.refreshPromise;
    this.refreshPromise = this.performRefresh();
    try {
      await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async performRefresh(): Promise<void> {
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
      await this.acceptTokenResponse(response);
    } catch (error) {
      if (error instanceof MobileApiError && [400, 401].includes(error.status)) {
        await this.clear();
      }
      throw error;
    }
  }

  private async acceptTokenResponse(response: Response): Promise<void> {
    const payload = (await response.json()) as OAuthTokenResponse | OAuthErrorResponse;
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
    await this.storage.set(this.tokens);
  }
}
