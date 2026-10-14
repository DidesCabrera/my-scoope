import assert from "node:assert/strict";
import test from "node:test";
import { MobileApiError } from "../src/api/errors";
import { storeBillingError } from "../src/billing/store-errors";

test("offline restore shows a human error and never exposes native exception details", () => {
  const raw = "UnexpectedException: No se pudo completar la operación. (Error de NSURLErrorDomain -1004) (at ExpoModulesCore/ConcurrentFunctionDefinition.swift:90)";
  for (const error of [new Error(raw), { message: raw }, { code: "E_NETWORK_ERROR", message: raw }]) {
    assert.equal(storeBillingError(error, "restore"), "No pudimos conectarnos con Apple. Revisa tu conexión e inténtalo nuevamente.");
    assert.doesNotMatch(storeBillingError(error), /NSURLErrorDomain|ExpoModulesCore|Swift|UnexpectedException/);
  }
});

test("verified server failures keep their specific account and retry guidance", () => {
  assert.equal(storeBillingError(new MobileApiError("internal", "apple_transaction_mismatch", 422), "restore"),
    "La transacción no corresponde a esta cuenta, producto o entorno de la tienda.");
});
