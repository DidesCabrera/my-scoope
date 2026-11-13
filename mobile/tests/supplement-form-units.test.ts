import assert from "node:assert/strict";
import test from "node:test";

import { defaultUnitForSupplementForm, editableSupplementForm, supplementForms } from "../src/components/supplements/supplement-form-units";

test("supplement form offers every dose unit and resolves a single default unit", () => {
  for (const unit of ["ml", "g", "mg", "mcg", "iu", "scoop", "tsp"]) {
    assert.ok(supplementForms.includes(unit as typeof supplementForms[number]));
    assert.equal(defaultUnitForSupplementForm(unit), unit);
  }
  assert.equal(defaultUnitForSupplementForm("powder"), "g");
  assert.equal(defaultUnitForSupplementForm("liquid"), "ml");
});

test("editing an older supplement preserves its dose unit when form and unit differ", () => {
  assert.equal(editableSupplementForm("capsule", "mg"), "mg");
  assert.equal(editableSupplementForm("powder", "g"), "powder");
  assert.equal(editableSupplementForm("liquid", "ml"), "liquid");
  assert.equal(editableSupplementForm("", "mcg"), "mcg");
});
