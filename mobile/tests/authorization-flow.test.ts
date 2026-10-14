import assert from "node:assert/strict";
import test from "node:test";
import { AuthorizationFlow } from "../src/auth/authorization-flow";

test("an old browser callback cannot exchange credentials for the new account attempt", async () => {
  const flow = new AuthorizationFlow();
  let exchanges = 0;
  flow.start("account-a-nonce");
  flow.invalidate();
  flow.start("account-b-nonce");
  assert.equal(await flow.complete("account-a-nonce", async () => { exchanges += 1; return "account-a"; }), null);
  assert.equal(exchanges, 0);
  assert.equal(await flow.complete("account-b-nonce", async () => "account-b"), "account-b");
});

test("logout or a newer attempt discards a delayed identity response", async () => {
  const flow = new AuthorizationFlow();
  let finish: ((value: string) => void) | undefined;
  flow.start("nonce-a");
  const old = flow.complete("nonce-a", () => new Promise<string>((resolve) => { finish = resolve; }));
  flow.invalidate();
  flow.start("nonce-b");
  finish!("account-a");
  assert.equal(await old, null);
  assert.equal(await flow.complete("nonce-b", async () => "account-b"), "account-b");
});

test("an outdated failed login cannot overwrite the current attempt's error", async () => {
  const flow = new AuthorizationFlow();
  let fail: ((error: Error) => void) | undefined;
  flow.start("old");
  const old = flow.complete("old", () => new Promise<string>((_resolve, reject) => { fail = reject; }));
  flow.start("current");
  fail!(new Error("old connection failed"));
  assert.equal(await old, null);
  await assert.rejects(flow.complete("current", async () => { throw new Error("current connection failed"); }), /current connection failed/);
});
