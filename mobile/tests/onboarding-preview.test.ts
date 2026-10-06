import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("login renders the first storyboard view with the real authentication action", async () => {
  const login = await source("src/app/login.tsx");

  assert.match(login, /OnboardingJourneyView/);
  assert.match(login, /step="login"/);
  assert.match(login, /startSignIn\(returnHref\)/);
});

test("staff can traverse a side-effect-free onboarding preview", async () => {
  const [preview, navigation] = await Promise.all([
    source("src/app/onboarding-preview.tsx"),
    source("src/components/navigation/app-navigation.tsx"),
  ]);

  assert.match(navigation, /session\?\.is_staff[\s\S]*Vista previa del onboarding/);
  assert.match(preview, /if \(!session\.is_staff\) return <Redirect href="\/account"/);
  assert.match(preview, /onboardingJourneySteps\.length - 1/);
  assert.doesNotMatch(preview, /apiRequest|\/api\/v1\//);
});
