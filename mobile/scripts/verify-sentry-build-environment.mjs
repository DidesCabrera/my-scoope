#!/usr/bin/env node

const target = process.env.MYSCOOPE_BUILD_TARGET ?? "local";
const uploadDisabled = process.env.SENTRY_DISABLE_AUTO_UPLOAD === "true";

if (target === "local" || uploadDisabled) process.exit(0);

const required = [
  "EXPO_PUBLIC_SENTRY_DSN",
  "SENTRY_AUTH_TOKEN",
  "SENTRY_ORG",
  "SENTRY_PROJECT",
];
const missing = required.filter((name) => !process.env[name]?.trim());

if (missing.length > 0) {
  process.stderr.write(`Configuración Sentry incompleta para ${target}: faltan ${missing.join(", ")}\n`);
  process.exit(1);
}

process.stdout.write(`Configuración Sentry lista para ${target}; source maps y símbolos serán publicados.\n`);
