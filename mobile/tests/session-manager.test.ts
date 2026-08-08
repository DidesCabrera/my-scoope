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
  const calls: Array<{ url: string; init?: RequestInit }> = [];
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
