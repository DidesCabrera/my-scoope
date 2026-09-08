#!/usr/bin/env node

import { execFileSync, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const mobileRoot = resolve(scriptDirectory, "..");
const repositoryRoot = resolve(mobileRoot, "..");
const require = createRequire(import.meta.url);
const { resolveDeploymentTarget } = require("../config/deployment-targets.js");
const easConfig = JSON.parse(readFileSync(resolve(mobileRoot, "eas.json"), "utf8"));

function fail(message) {
  process.stderr.write(`Configuración móvil rechazada: ${message}\n`);
  process.exit(1);
}

function resolveProfile(profileName, visited = new Set()) {
  const profile = easConfig.build?.[profileName];
  if (!profile) throw new Error(`No existe el perfil EAS ${profileName}`);
  if (visited.has(profileName)) throw new Error(`Herencia circular en el perfil EAS ${profileName}`);
  if (!profile.extends) return profile;

  visited.add(profileName);
  const parent = resolveProfile(profile.extends, visited);
  return {
    ...parent,
    ...profile,
    env: { ...(parent.env ?? {}), ...(profile.env ?? {}) },
    ios: { ...(parent.ios ?? {}), ...(profile.ios ?? {}) },
  };
}

function verifyProfile(profileName) {
  const profile = resolveProfile(profileName);
  const target = resolveDeploymentTarget(profile.env ?? {});

  if (profileName === "simulator-staging") {
    if (target.key !== "staging") throw new Error("simulator-staging no apunta a staging");
    if (!profile.developmentClient || profile.ios?.simulator !== true) {
      throw new Error("simulator-staging debe ser un development client para iOS Simulator");
    }
  }

  if (["testflight-production", "production"].includes(profileName)) {
    if (target.key !== "production") throw new Error(`${profileName} no apunta a producción`);
    if (profile.developmentClient || profile.ios?.simulator) {
      throw new Error(`${profileName} no puede ser un development client ni una build de simulador`);
    }
    if (profile.autoIncrement !== true) throw new Error(`${profileName} debe incrementar el build number`);
  }

  return { profile, target };
}

function git(...arguments_) {
  return execFileSync("git", arguments_, { cwd: repositoryRoot, encoding: "utf8" }).trim();
}

function verifySourcePolicy(profileName, target) {
  const branch = git("branch", "--show-current");

  if (target.key === "staging" && branch === "main") {
    throw new Error("main no debe ejecutarse contra staging; cambia a staging o a una rama de trabajo");
  }
  if (target.key !== "production") return;
  if (branch !== "main") throw new Error(`una build de producción exige la rama main; rama actual: ${branch || "detached HEAD"}`);
  if (git("status", "--porcelain")) throw new Error("una build de producción exige un árbol de trabajo limpio");

  const upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}");
  if (upstream !== "origin/main") throw new Error(`main debe seguir origin/main; upstream actual: ${upstream}`);
  if (git("rev-parse", "HEAD") !== git("rev-parse", "@{upstream}")) {
    throw new Error("main debe estar exactamente sincronizada con origin/main antes de construir producción");
  }
}

function verifyConfiguration() {
  if (easConfig.cli?.requireCommit !== true) throw new Error("EAS debe exigir un commit limpio");
  if (easConfig.build?.testflight) throw new Error("el perfil ambiguo testflight no debe existir");
  for (const profileName of ["development", "simulator-staging", "preview", "testflight-production", "production"]) {
    const { target } = verifyProfile(profileName);
    process.stdout.write(`${profileName}: ${target.key} -> ${target.apiBaseUrl}\n`);
  }
}

const arguments_ = process.argv.slice(2);
if (arguments_[0] === "--verify") {
  try {
    verifyConfiguration();
  } catch (error) {
    fail(error instanceof Error ? error.message : String(error));
  }
  process.exit(0);
}

const profileName = arguments_[0];
if (!profileName) fail("indica un perfil EAS");

let resolved;
try {
  verifyConfiguration();
  resolved = verifyProfile(profileName);
  verifySourcePolicy(profileName, resolved.target);
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}

const separator = arguments_.indexOf("--");
if (separator === -1) {
  process.stdout.write(`Perfil seguro: ${profileName} (${resolved.target.key}) -> ${resolved.target.apiBaseUrl}\n`);
  process.exit(0);
}

const [command, ...commandArguments] = arguments_.slice(separator + 1);
if (!command) fail("falta el comando después de --");

const result = spawnSync(command, commandArguments, {
  cwd: mobileRoot,
  env: { ...process.env, ...(resolved.profile.env ?? {}) },
  stdio: "inherit",
});

if (result.error) fail(result.error.message);
process.exit(result.status ?? 1);
