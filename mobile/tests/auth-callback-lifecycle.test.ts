import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("OAuth request survives navigation from login to the native callback", async () => {
  const [provider, login, callback] = await Promise.all([
    source("src/auth/session-context.tsx"),
    source("src/app/login.tsx"),
    source("src/app/oauth/callback.tsx"),
  ]);

  assert.match(provider, /useAuthRequest\(/);
  assert.match(provider, /Linking\.addEventListener\("url"/);
  assert.match(provider, /parseReturnUrl\(url\)/);
  assert.doesNotMatch(login, /useAuthRequest\(/);
  assert.match(callback, /status === "authenticated"/);
  assert.match(callback, /Volver a iniciar sesión/);
});
