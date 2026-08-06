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

export type SessionManagerConfig = {
  apiBaseUrl: string;
  oauthClientId: string;
  oauthRedirectUri: string;
  oauthTokenEndpoint: string;
};

const REFRESH_SKEW_MS = 60_000;

export class MobileSessionManager {
  private tokens: StoredTokenSet | null = null;

  constructor(
    private readonly config: SessionManagerConfig,
    private readonly storage: TokenStorage,
    private readonly getDeviceIdentity: () => Promise<DeviceIdentity>,
    private readonly fetchImpl: FetchLike = fetch,
    private readonly now: () => number = Date.now,
  ) {}

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

    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${this.tokens.accessToken}`);
    if (init.body && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const response = await this.fetchImpl(`${this.config.apiBaseUrl}${path}`, {
      ...init,
      headers,
    });

    if (response.status === 401 && canRetry) {
      await this.refresh();
      return this.request<T>(path, init, false);
    }
    const payload = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || !payload.ok) {
      const detail = payload.ok
        ? { code: "mobile_api_error", message: "La solicitud no pudo completarse.", details: {} }
        : payload.error;
      throw new MobileApiError(detail.message, detail.code, response.status, detail.details);
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
    await this.storage.clear();
  }

  private accessNeedsRefresh(): boolean {
    return !this.tokens || this.tokens.accessExpiresAt <= this.now() + REFRESH_SKEW_MS;
  }

  private async refresh(): Promise<void> {
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
