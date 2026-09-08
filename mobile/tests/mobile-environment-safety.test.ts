import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
import { readFile } from "node:fs/promises";
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
  const eas = JSON.parse(await readFile(path.resolve(process.cwd(), "eas.json"), "utf8"));
  const packageJson = JSON.parse(await readFile(path.resolve(process.cwd(), "package.json"), "utf8"));

  assert.equal(eas.cli.requireCommit, true);
  assert.equal(eas.build.testflight, undefined);
  assert.equal(eas.build["simulator-staging"].ios.simulator, true);
  assert.equal(eas.build["simulator-staging"].env.EXPO_PUBLIC_API_BASE_URL, "https://myscoope-staging.onrender.com");
  assert.equal(eas.build["testflight-production"].env.EXPO_PUBLIC_API_BASE_URL, "https://www.myscoope.com");
  assert.equal(eas.build.production.extends, "testflight-production");
  assert.match(packageJson.scripts["start:staging"], /mobile-environment-command\.mjs simulator-staging/);
  assert.match(packageJson.scripts["build:production"], /mobile-environment-command\.mjs testflight-production/);
  assert.doesNotMatch(packageJson.scripts["build:production"], /auto-submit/);

  const verification = execFileSync(
    process.execPath,
    [path.resolve(process.cwd(), "scripts/mobile-environment-command.mjs"), "--verify"],
    { encoding: "utf8" },
  );
  assert.match(verification, /simulator-staging: staging -> https:\/\/myscoope-staging\.onrender\.com/);
  assert.match(verification, /testflight-production: production -> https:\/\/www\.myscoope\.com/);
});
