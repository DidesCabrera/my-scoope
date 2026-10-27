import assert from "node:assert/strict";
import test from "node:test";

import { MobileSessionManager, type StoredTokenSet, type TokenStorage } from "../src/auth/session-manager";
import { createCalendarMonthCache } from "../src/components/calendarization/calendar-month-cache";

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

test("purchase revalidation bypasses cached and in-flight billing snapshots", async () => {
  let reads = 0;
  const manager = new MobileSessionManager(config, storage(), async () => ({ id: "device", name: "iPhone", platform: "ios" }),
    (async (input) => String(input).endsWith("/oauth/token") ? jsonResponse(tokenResponse("fresh")) :
      jsonResponse({ ok: true, data: String(input).endsWith("/subscriptions") ? { plan: ++reads === 1 ? "Basic" : "Pro" } : sessionData, error: null })) as typeof fetch,
    () => now);
  await manager.exchangeAuthorizationCode("code", "verifier");
  assert.equal((await manager.request<{ plan: string }>("/api/v1/subscriptions")).plan, "Basic");
  assert.equal((await manager.request<{ plan: string }>("/api/v1/subscriptions", { cache: "no-store" })).plan, "Pro");
  assert.equal(reads, 2);
});

test("a delayed response from an old account is rejected after logout", async () => {
  let release!: (value: Response) => void;
  const manager = new MobileSessionManager(config, storage(), async () => ({ id: "device", name: "iPhone", platform: "ios" }),
    (async (input) => String(input).endsWith("/oauth/token") ? jsonResponse(tokenResponse("a")) :
      String(input).endsWith("/subscriptions") ? new Promise<Response>((resolve) => { release = resolve; }) :
        jsonResponse({ ok: true, data: sessionData, error: null })) as typeof fetch, () => now);
  await manager.exchangeAuthorizationCode("code", "verifier");
  const read = manager.request("/api/v1/subscriptions");
  await manager.clear();
  release(jsonResponse({ ok: true, data: { plan_name: "Pro" }, error: null }));
  await assert.rejects(read, /sesión cambió/);
});

test("logout while a token refresh is in flight cannot recreate credentials", async () => {
  let time = now;
  let release!: (value: Response) => void;
  let issued = 0;
  const saved = storage();
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "device", name: "iPhone", platform: "ios" }),
    (async (input) => String(input).endsWith("/oauth/token") ? (++issued === 1 ? jsonResponse(tokenResponse("a")) :
      new Promise<Response>((resolve) => { release = resolve; })) : jsonResponse({ ok: true, data: sessionData, error: null })) as typeof fetch, () => time);
  await manager.exchangeAuthorizationCode("code", "verifier");
  time += 900_000;
  const read = manager.request("/api/v1/subscriptions");
  await manager.clear();
  release(jsonResponse(tokenResponse("late")));
  await assert.rejects(read, /sesión cambió/);
  assert.equal(saved.current, null);
});

test("a transient startup outage keeps credentials and can restore without another login", async () => {
  const saved = storage();
  let offline = false;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "device", name: "iPhone", platform: "ios" }),
    (async (input) => {
      if (offline) throw new Error("offline");
      return String(input).endsWith("/oauth/token") ? jsonResponse(tokenResponse("a")) :
        jsonResponse({ ok: true, data: sessionData, error: null });
    }) as typeof fetch, () => now);
  await manager.exchangeAuthorizationCode("code", "verifier");
  const restarted = new MobileSessionManager(config, saved, async () => ({ id: "device", name: "iPhone", platform: "ios" }),
    (async () => { if (offline) throw new Error("offline"); return jsonResponse({ ok: true, data: sessionData, error: null }); }) as typeof fetch, () => now);
  offline = true;
  await assert.rejects(restarted.restore(), /offline/);
  assert.equal(saved.current?.refreshToken, "refresh-a");
  offline = false;
  assert.equal((await restarted.restore())?.user_id, sessionData.user_id);
});

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

test("request metrics keep a safe server correlation id and normalized route", async () => {
  const saved = storage({
    accessToken: "access-current",
    refreshToken: "refresh-current",
    accessExpiresAt: now + 100_000,
    refreshExpiresAt: now + 200_000,
    scope: "mobile:read",
    deviceSessionId: "device-session-1",
  });
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }),
    (async (input) => new Response(JSON.stringify({ ok: true, data: String(input).endsWith("/session") ? sessionData : { value: 1 }, error: null }), {
      headers: { "Content-Type": "application/json", "Rndr-Id": "req-beta_123" },
    })) as typeof fetch, () => now);
  const metrics: Parameters<Parameters<typeof manager.setRequestMetricObserver>[0]>[0][] = [];
  manager.setRequestMetricObserver((metric) => metrics.push(metric));
  await manager.restore();
  await manager.request("/api/v1/program/days/42?private=secret", { cache: "no-store" });

  assert.equal(metrics.at(-1)?.path, "/api/v1/program/days/:id");
  assert.equal(metrics.at(-1)?.requestId, "req-beta_123");
  assert.equal(metrics.at(-1)?.outcome, "success");
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

test("calendar writes invalidate overview responses and shared month data", async () => {
  const saved = storage({
    accessToken: "access-current",
    refreshToken: "refresh-current",
    accessExpiresAt: now + 100_000,
    refreshExpiresAt: now + 200_000,
    scope: "mobile:read mobile:write",
    deviceSessionId: "device-session-1",
  });
  let reads = 0;
  const fetchMock = (async (input: string | URL | Request, init?: RequestInit) => {
    if (String(input).endsWith("/api/v1/session")) return jsonResponse({ ok: true, data: sessionData, error: null });
    if ((init?.method ?? "GET") !== "GET") return jsonResponse({ ok: true, data: {}, error: null });
    reads += 1;
    return jsonResponse({ ok: true, data: {
      days: [], end_date: "2026-10-31", local_date: `2026-10-${String(reads).padStart(2, "0")}`, start_date: "2026-10-01",
    }, error: null });
  }) as typeof fetch;
  const manager = new MobileSessionManager(config, saved, async () => ({ id: "unused", name: "unused", platform: "ios" }), fetchMock, () => now);
  await manager.restore();
  const apiRequest = <T>(path: string, init?: RequestInit) => manager.request<T>(path, init);
  const monthCache = createCalendarMonthCache(apiRequest);

  await monthCache.load("2026-10");
  const overview = await manager.request<{ local_date: string }>("/api/v1/calendar?days=35");
  await manager.request("/api/v1/calendar/days/2026-10-27/plan", { method: "DELETE" });

  assert.equal(monthCache.get("2026-10"), undefined);
  assert.notEqual((await monthCache.load("2026-10")).local_date, "2026-10-01");
  assert.notEqual((await manager.request<{ local_date: string }>("/api/v1/calendar?days=35")).local_date, overview.local_date);
});
