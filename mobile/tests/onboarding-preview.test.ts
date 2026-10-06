import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("login renders the first storyboard view with the real authentication action", async () => {
  const login = await source("src/app/login.tsx");

  assert.ok(login.includes("OnboardingJourneyView"));
  assert.ok(login.includes('step="login"'));
  assert.ok(login.includes("startSignIn(returnHref)"));
});

test("staff can traverse a side-effect-free onboarding preview", async () => {
  const [preview, navigation] = await Promise.all([
    source("src/app/onboarding-preview.tsx"),
    source("src/components/navigation/app-navigation.tsx"),
  ]);

  assert.ok(navigation.includes("session?.is_staff"));
  assert.ok(navigation.includes("Vista previa del onboarding"));
  assert.ok(preview.includes('if (!session.is_staff) return <Redirect href="/account"'));
  assert.ok(preview.includes("onboardingJourneySteps.length - 1"));
  assert.ok(!preview.includes("apiRequest"));
  assert.ok(!preview.includes("/api/v1/"));
});
