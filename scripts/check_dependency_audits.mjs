#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const budget = JSON.parse(
  readFileSync(path.join(root, "config/dependency_audit_budget.json"), "utf8"),
);
const severityRank = { info: 0, low: 1, moderate: 2, high: 3, critical: 4 };

function auditSurface(name, cwd) {
  const result = spawnSync("npm", ["audit", "--omit=dev", "--json"], {
    cwd,
    encoding: "utf8",
  });
  if (![0, 1].includes(result.status) || !result.stdout.trim()) {
    throw new Error(`${name}: npm audit could not complete: ${result.stderr.trim() || `exit ${result.status}`}`);
  }

  let report;
  try {
    report = JSON.parse(result.stdout);
  } catch (error) {
    throw new Error(`${name}: npm audit returned invalid JSON: ${error.message}`);
  }

  const allowed = budget[name]?.allowed ?? {};
  const findings = [];
  for (const [packageName, detail] of Object.entries(report.vulnerabilities ?? {})) {
    const severity = detail.severity;
    const allowedSeverity = allowed[packageName];
    if (severity === "critical") {
      findings.push(`${packageName}: critical advisories are never allowlisted`);
    } else if (!allowedSeverity) {
      findings.push(`${packageName}: new ${severity} advisory is not in the reviewed budget`);
    } else if (severityRank[severity] > severityRank[allowedSeverity]) {
      findings.push(`${packageName}: severity ${severity} exceeds reviewed ${allowedSeverity}`);
    }
  }

  if (findings.length) {
    throw new Error(`${name} dependency audit failed:\n- ${findings.join("\n- ")}`);
  }

  const counts = report.metadata?.vulnerabilities ?? {};
  console.log(
    `${name} dependency audit passed: ${counts.total ?? 0} reviewed findings ` +
      `(${counts.high ?? 0} high, ${counts.moderate ?? 0} moderate, ${counts.critical ?? 0} critical).`,
  );
}

try {
  auditSurface("root", root);
  auditSurface("mobile", path.join(root, "mobile"));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
