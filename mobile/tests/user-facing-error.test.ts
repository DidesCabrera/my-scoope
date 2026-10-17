import assert from "node:assert/strict";
import test from "node:test";
import { MobileApiError, userFacingError } from "../src/api/errors";

const raw = "fetch failed: UnexpectedException: La conexión a Internet parece estar desactivada. (at ExpoModulesCore/Promise.swift:56)";
test("Cuenta, Suscripciones and Today sanitize the actual build 40 Expo fetch failure", () => {
  for (const error of [new Error(raw), { message: raw }, { cause: new Error(raw) }, { nativeError: { message: raw } }, new MobileApiError(raw, "unmapped", 500)]) {
    assert.equal(userFacingError(error), "No pudimos conectarnos. Revisa tu conexión e inténtalo nuevamente.");
  }
});
test("native internals and multiline stacks never become a user message", () => {
  for (const text of ["UnexpectedException: failure", "ExpoModulesCore/ConcurrentFunctionDefinition.swift:90", "Swift failed", "problem\n at internalFunction (file.ts:10)", "TypeError: invalid value"]) {
    for (const error of [new Error(text), new MobileApiError(text, "unmapped", 400)]) {
      assert.equal(userFacingError(error), "No pudimos completar la acción. Inténtalo nuevamente.");
    }
  }
});
test("native error traversal is bounded and preserves owned validation guidance", () => {
  const cyclic: { cause?: unknown } = {};
  cyclic.cause = cyclic;
  assert.equal(userFacingError(cyclic), "No pudimos completar la acción. Inténtalo nuevamente.");
  assert.equal(userFacingError(new MobileApiError("internal", "apple_transaction_mismatch", 422)), "La transacción no corresponde a esta cuenta, producto o entorno de la tienda.");
  assert.equal(userFacingError(new Error("Ingresa un nombre antes de guardar.")), "Ingresa un nombre antes de guardar.");
});
