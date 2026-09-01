#!/usr/bin/env node

import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const testRoot = path.join(root, "mobile/tests");
const budget = JSON.parse(
  readFileSync(path.join(root, "config/mobile_test_debt_budget.json"), "utf8"),
);
let sourceReads = 0;
let sourceRegexAssertions = 0;

for (const name of readdirSync(testRoot).filter((value) => value.endsWith(".test.ts"))) {
  const source = readFileSync(path.join(testRoot, name), "utf8");
  sourceReads += source.match(/\breadFile\s*\(/g)?.length ?? 0;
  sourceRegexAssertions += source.match(/assert\.(?:doesNotMatch|match)\s*\(/g)?.length ?? 0;
}

const findings = [];
if (sourceReads > budget.max_source_reads) {
  findings.push(`${sourceReads} source reads > ${budget.max_source_reads}`);
}
if (sourceRegexAssertions > budget.max_source_regex_assertions) {
  findings.push(`${sourceRegexAssertions} source-regex assertions > ${budget.max_source_regex_assertions}`);
}
if (findings.length) {
  console.error(`Mobile test debt budget failed:\n- ${findings.join("\n- ")}`);
  process.exitCode = 1;
} else {
  console.log(
    `Mobile test debt budget passed: ${sourceReads} source reads, ` +
      `${sourceRegexAssertions} source-regex assertions.`,
  );
}
