import path from "node:path";
import test from "node:test";

import { assertSourceDoesNotMatch, assertSourceMatch, readTestFile } from "./support/source-contract";

test("startup keeps the native splash through session restoration and leaves one Home loader", async () => {
  const layout = await readTestFile(path.resolve(process.cwd(), "src/app/_layout.tsx"), "utf8");
  const index = await readTestFile(path.resolve(process.cwd(), "src/app/index.tsx"), "utf8");
  const today = await readTestFile(path.resolve(process.cwd(), "src/app/today.tsx"), "utf8");

  assertSourceMatch(layout, /SplashScreen\.preventAutoHideAsync\(\)/);
  assertSourceMatch(layout, /function SplashCoordinator\(\)[\s\S]*status === "booting"[\s\S]*requestAnimationFrame[\s\S]*SplashScreen\.hideAsync\(\)/);
  assertSourceMatch(layout, /<SessionProvider>\s*<SplashCoordinator \/>/);
  assertSourceMatch(index, /status === "booting"\) return null/);
  assertSourceDoesNotMatch(index, /LoadingState/);
  assertSourceMatch(today, /if \(loading && !today\) return <>\s*<Stack\.Screen options=\{\{ headerShown: false \}\} \/>\s*<LoadingState \/>\s*<\/>/);
  assertSourceMatch(today, /<Stack\.Screen options=\{\{ headerShown: true \}\} \/>\s*<Screen headerMode="preserve">/);
});
