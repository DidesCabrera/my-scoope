import assert from "node:assert/strict";
import test from "node:test";

import { MobileSessionManager, type StoredTokenSet, type TokenStorage } from "../src/auth/session-manager";

const now = 1_800_000_000_000;
const config = {
  apiBaseUrl: "https://staging.myscoope.test",
  oauthClientId: "myscoope-ios",
  oauthRedirectUri: "myscoope://oauth/callback",
  oauthTokenEndpoint: "https://staging.myscoope.test/oauth/token",
};
const sessionData = {
  user_id: 7,
  username: "felipe",
  email: "felipe@example.com",
  display_name: "Felipe",
  scopes: ["mobile:read", "mobile:write", "mobile:account"],
  device_session_id: "device-session-1",
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function tokenResponse(suffix: string) {
  return {
    access_token: `access-${suffix}`,
    refresh_token: `refresh-${suffix}`,
    token_type: "Bearer",
    expires_in: 900,
    refresh_expires_in: 2_592_000,
    scope: "mobile:read mobile:write mobile:account",
    device_session_id: "device-session-1",
  };
}

function storage(initial: StoredTokenSet | null = null): TokenStorage & { current: StoredTokenSet | null } {
  return {
    current: initial,
    async get() { return this.current; },
    async set(tokens) { this.current = tokens; },
    async clear() { this.current = null; },
  };
}

test("authorization-code exchange binds the device and stores the rotating pair", async () => {
  const saved = storage();
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetchMock = (async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(input), init });
    if (calls.length === 1) return jsonResponse(tokenResponse("one"));
    return jsonResponse({ ok: true, data: sessionData, error: null });
  }) as typeof fetch;
  const manager = new MobileSessionManager(
    config,
    saved,
    async () => ({ id: "device-id-123456789", name: "iPhone de Felipe", platform: "ios" }),
    fetchMock,
    () => now,
  );

  const session = await manager.exchangeAuthorizationCode("code-1", "verifier-1");

  assert.equal(session.user_id, 7);
  assert.equal(saved.current?.refreshToken, "refresh-one");
  const form = new URLSearchParams(String(calls[0].init?.body));
  assert.equal(form.get("device_id"), "device-id-123456789");
  assert.equal(form.get("code_verifier"), "verifier-1");
  assert.equal(form.get("redirect_uri"), config.oauthRedirectUri);
  assert.equal(new Headers(calls[1].init?.headers).get("Authorization"), "Bearer access-one");
});

test("restore rotates an expired access token before requesting the session", async () => {
  const saved = storage({
    accessToken: "access-old",
    refreshToken: "refresh-old",
    accessExpiresAt: now - 1,
    refreshExpiresAt: now + 100_000,
    scope: "mobile:read",
    deviceSessionId: "device-session-1",
  });
  const calls: string[] = [];
  const fetchMock = (async (input: string | URL | Request) => {
    calls.push(String(input));
    if (calls.length === 1) return jsonResponse(tokenResponse("rotated"));
    return jsonResponse({ ok: true, data: sessionData, error: null });
  }) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => now);

  const restored = await manager.restore();

  assert.equal(restored?.username, "felipe");
  assert.deepEqual(calls, [config.oauthTokenEndpoint, `${config.apiBaseUrl}/api/v1/session`]);
  assert.equal(saved.current?.accessToken, "access-rotated");
});

test("refresh failure clears local credentials", async () => {
  const saved = storage({
    accessToken: "access-old",
    refreshToken: "refresh-old",
    accessExpiresAt: now - 1,
    refreshExpiresAt: now + 100_000,
    scope: "mobile:read",
    deviceSessionId: "device-session-1",
  });
  const fetchMock = (async () => jsonResponse({ error: "invalid_grant", error_description: "Revocado" }, 400)) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => now);

  assert.equal(await manager.restore(), null);
  assert.equal(saved.current, null);
});

test("non-JSON API responses become a bounded product error", async () => {
  const saved = storage({
    accessToken: "access-current",
    refreshToken: "refresh-current",
    accessExpiresAt: now + 100_000,
    refreshExpiresAt: now + 200_000,
    scope: "mobile:read mobile:write",
    deviceSessionId: "device-session-1",
  });
  let calls = 0;
  const fetchMock = (async () => {
    calls += 1;
    if (calls === 1) return jsonResponse({ ok: true, data: sessionData, error: null });
    return new Response("<!doctype html><title>Not found</title>", {
      status: 404,
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  }) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => now);
  await manager.restore();

  await assert.rejects(
    manager.request("/api/v1/program/days/1/meal-picker/preview"),
    (error: unknown) => error instanceof Error
      && "code" in error
      && error.code === "mobile_api_invalid_response"
      && error.message === "Esta función todavía no está disponible en el servidor seleccionado.",
  );
});

test("concurrent reads are deduplicated and fresh data is reused", async () => {
  const saved = storage({
    accessToken: "access-current",
    refreshToken: "refresh-current",
    accessExpiresAt: now + 100_000,
    refreshExpiresAt: now + 200_000,
    scope: "mobile:read",
    deviceSessionId: "device-session-1",
  });
  let calls = 0;
  let release: (() => void) | undefined;
  const blocked = new Promise<void>((resolve) => { release = resolve; });
  const fetchMock = (async (input: string | URL | Request) => {
    calls += 1;
    if (String(input).endsWith("/api/v1/session")) {
      return jsonResponse({ ok: true, data: sessionData, error: null });
    }
    await blocked;
    return jsonResponse({ ok: true, data: { value: 42 }, error: null });
  }) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => now);
  await manager.restore();

  const first = manager.request<{ value: number }>("/api/v1/home");
  const second = manager.request<{ value: number }>("/api/v1/home");
  release?.();

  assert.deepEqual(await Promise.all([first, second]), [{ value: 42 }, { value: 42 }]);
  assert.deepEqual(await manager.request("/api/v1/home"), { value: 42 });
  assert.equal(calls, 2);
});

test("stale reads revalidate with ETag and reuse a 304 response", async () => {
  let clock = now;
  const saved = storage({
    accessToken: "access-current",
    refreshToken: "refresh-current",
    accessExpiresAt: now + 100_000,
    refreshExpiresAt: now + 200_000,
    scope: "mobile:read",
    deviceSessionId: "device-session-1",
  });
  const headers: (string | null)[] = [];
  const fetchMock = (async (input: string | URL | Request, init?: RequestInit) => {
    if (String(input).endsWith("/api/v1/session")) {
      return jsonResponse({ ok: true, data: sessionData, error: null });
    }
    headers.push(new Headers(init?.headers).get("If-None-Match"));
    if (headers.length === 1) {
      return new Response(JSON.stringify({ ok: true, data: { value: 7 }, error: null }), {
        headers: { "Content-Type": "application/json", ETag: 'W/"home-v1"' },
      });
    }
    return new Response(null, { status: 304, headers: { ETag: 'W/"home-v1"' } });
  }) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => clock);
  await manager.restore();

  assert.deepEqual(await manager.request("/api/v1/home"), { value: 7 });
  clock += 21_000;
  assert.deepEqual(await manager.request("/api/v1/home"), { value: 7 });
  assert.deepEqual(headers, [null, 'W/"home-v1"']);
});

test("a mutation invalidates affected cached reads", async () => {
  const saved = storage({
    accessToken: "access-current",
    refreshToken: "refresh-current",
    accessExpiresAt: now + 100_000,
    refreshExpiresAt: now + 200_000,
    scope: "mobile:read mobile:write",
    deviceSessionId: "device-session-1",
  });
  let homeCalls = 0;
  const fetchMock = (async (input: string | URL | Request, init?: RequestInit) => {
    if (String(input).endsWith("/api/v1/session")) {
      return jsonResponse({ ok: true, data: sessionData, error: null });
    }
    if ((init?.method ?? "GET") !== "GET") {
      return jsonResponse({ ok: true, data: { id: 1 }, error: null });
    }
    homeCalls += 1;
    return jsonResponse({ ok: true, data: { version: homeCalls }, error: null });
  }) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => now);
  await manager.restore();

  assert.deepEqual(await manager.request("/api/v1/home"), { version: 1 });
  await manager.request("/api/v1/weights", { body: JSON.stringify({ weight_kg: 80 }), method: "POST" });
  assert.deepEqual(await manager.request("/api/v1/home"), { version: 2 });
});
