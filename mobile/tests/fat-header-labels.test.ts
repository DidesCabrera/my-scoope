import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import ts from "typescript";

function displayedLabels(source: string, file: string): string[] {
  const parsed = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const labels: string[] = [];
  const visit = (node: ts.Node) => {
    if (ts.isStringLiteral(node) || ts.isJsxText(node)) labels.push(node.text.trim());
    ts.forEachChild(node, visit);
  };
  visit(parsed);
  return labels;
}

test("fat panel headers and comparison legends use G for grasas", async () => {
  const files = [
    "src/components/panels/entity-panels.tsx",
    "src/components/calendarization/calendar-upcoming-panels.tsx",
    "src/components/libraries/program-day-comparison-panels.tsx",
    "src/components/libraries/program-week-comparison-panels.tsx",
    "src/components/comparisons/comparison-result.tsx",
    "src/sharing/presentation.ts",
  ];
  for (const file of files) {
    const source = await readFile(path.resolve(process.cwd(), file), "utf8");
    const labels = displayedLabels(source, file);
    for (const oldLabel of ["F", "Fg", "F%", "P|C|F"]) {
      assert.ok(!labels.includes(oldLabel), `${file} todavía muestra ${oldLabel}`);
    }
  }

  const panels = displayedLabels(await readFile(path.resolve(process.cwd(), files[0]!), "utf8"), files[0]!);
  for (const newLabel of ["G", "G%", "P|C|G"]) {
    assert.ok(panels.includes(newLabel), `El panel de alimentos debe mostrar ${newLabel}`);
  }
});
