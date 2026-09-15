import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string): Promise<string> {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("composition reordering shows immediate progress and self-closing success feedback", async () => {
  const detail = await source("src/components/libraries/library-detail-screen.tsx");
  const feedback = await source("src/components/ui/feedback.tsx");

  assert.match(detail, /loadingLabel: "Actualizando programa", successLabel: "Programa actualizado"/);
  assert.match(detail, /loadingLabel: "Actualizando plan", successLabel: "Plan actualizado"/);
  assert.match(detail, /loadingLabel: "Actualizando comida", successLabel: "Comida actualizada"/);
  assert.match(detail, /if \(feedback\) setMutationStatus\(\{ \.\.\.feedback, phase: "loading" \}\);[\s\S]*?await apiRequest/);
  assert.match(detail, /if \(feedback\) setMutationStatus\(\{ \.\.\.feedback, phase: "success" \}\);/);
  assert.match(feedback, /<ActivityIndicator/);
  assert.match(feedback, /status\?\.phase !== "success"/);
  assert.match(feedback, /setTimeout\(onFinished, 900\)/);
  assert.doesNotMatch(feedback, /<Button/);
});
