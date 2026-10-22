import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import path from "node:path";
import test from "node:test";

const require = createRequire(import.meta.url);
const { resolveDeploymentTarget } = require("../config/deployment-targets.js") as {
  resolveDeploymentTarget(environment: Record<string, string>): { apiBaseUrl: string; key: string };
};

test("mobile deployment targets fail closed when environment and API disagree", () => {
  assert.equal(resolveDeploymentTarget({
    MYSCOOPE_BUILD_TARGET: "staging",
    EXPO_PUBLIC_DEPLOYMENT_ENV: "staging",
    EXPO_PUBLIC_API_BASE_URL: "https://myscoope-staging.onrender.com",
  }).key, "staging");

  assert.throws(
    () => resolveDeploymentTarget({
      MYSCOOPE_BUILD_TARGET: "production",
      EXPO_PUBLIC_DEPLOYMENT_ENV: "production",
      EXPO_PUBLIC_API_BASE_URL: "https://myscoope-staging.onrender.com",
    }),
    /build production debe usar https:\/\/www\.myscoope\.com/,
  );
});

test("EAS keeps simulator staging separate from TestFlight production", async () => {
  const eas = require("../eas.json");
  const packageJson = require("../package.json");

  assert.equal(eas.cli.requireCommit, true);
  assert.equal(eas.build.testflight, undefined);
  assert.equal(eas.build["simulator-staging"].ios.simulator, true);
  assert.equal(eas.build["simulator-staging"].env.EXPO_PUBLIC_API_BASE_URL, "https://myscoope-staging.onrender.com");
  assert.equal(eas.build["testflight-production"].env.EXPO_PUBLIC_API_BASE_URL, "https://www.myscoope.com");
  assert.equal(eas.build["testflight-production"].uploadSourceMaps, true);
  assert.equal(eas.build["testflight-production"].env.SENTRY_DISABLE_AUTO_UPLOAD, undefined);
  assert.equal(eas.build["testflight-production"].env.EXPO_PUBLIC_SENTRY_TRACES_SAMPLE_RATE, "1");
  assert.equal(eas.build["testflight-staging"].extends, "testflight-production");
  assert.equal(eas.build["testflight-staging"].env.EXPO_PUBLIC_API_BASE_URL, "https://myscoope-staging.onrender.com");
  assert.equal(eas.build.production.extends, "testflight-production");
  assert.match(packageJson.scripts["start:staging"], /mobile-environment-command\.mjs simulator-staging/);
  assert.match(packageJson.scripts["build:production"], /mobile-environment-command\.mjs testflight-production/);
  assert.match(packageJson.scripts["build:ios:staging"], /mobile-environment-command\.mjs testflight-staging/);
  assert.match(packageJson.scripts["submit:ios:staging"], /mobile-environment-command\.mjs testflight-staging/);
  assert.doesNotMatch(packageJson.scripts["build:production"], /auto-submit/);
  assert.ok(packageJson.scripts["eas-build-post-install"].includes("verify-sentry-build-environment.mjs"));

  const verification = execFileSync(
    process.execPath,
    [path.resolve(process.cwd(), "scripts/mobile-environment-command.mjs"), "--verify"],
    { encoding: "utf8" },
  );
  assert.match(verification, /simulator-staging: staging -> https:\/\/myscoope-staging\.onrender\.com/);
  assert.match(verification, /testflight-production: production -> https:\/\/www\.myscoope\.com/);
  assert.match(verification, /testflight-staging: staging -> https:\/\/myscoope-staging\.onrender\.com/);
});

test("release builds fail closed when Sentry credentials are absent", () => {
  const script = path.resolve(process.cwd(), "scripts/verify-sentry-build-environment.mjs");
  const missing = spawnSync(process.execPath, [script], {
    encoding: "utf8",
    env: {
      ...process.env,
      EXPO_PUBLIC_SENTRY_DSN: "",
      MYSCOOPE_BUILD_TARGET: "production",
      SENTRY_AUTH_TOKEN: "",
      SENTRY_ORG: "",
      SENTRY_PROJECT: "",
    },
  });
  assert.equal(missing.status, 1);
  assert.ok(missing.stderr.includes("Configuración Sentry incompleta"));

  const configured = spawnSync(process.execPath, [script], {
    encoding: "utf8",
    env: {
      ...process.env,
      EXPO_PUBLIC_SENTRY_DSN: "https://public@example.invalid/1",
      MYSCOOPE_BUILD_TARGET: "production",
      SENTRY_AUTH_TOKEN: "token-for-test",
      SENTRY_ORG: "my-scoope",
      SENTRY_PROJECT: "mobile",
    },
  });
  assert.equal(configured.status, 0, configured.stderr);
  assert.ok(configured.stdout.includes("source maps y símbolos serán publicados"));
});
