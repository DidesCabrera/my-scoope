import assert from "node:assert/strict";
import test from "node:test";

import { heightFromValue, portionFromValue, weightPartsFromValue, weightValueFromParts } from "../src/components/ui/native-measurement-values";

test("height picker rounds and bounds persisted centimeter values", () => {
  assert.equal(heightFromValue("178.4"), 178);
  assert.equal(heightFromValue("20"), 80);
  assert.equal(heightFromValue("400"), 250);
});

test("weight picker converts decimals to kilograms and 100-gram steps", () => {
  assert.deepEqual(weightPartsFromValue("82,54"), { kilograms: 82, grams: 500 });
  assert.equal(weightValueFromParts(82, 500), "82.5");
  assert.equal(weightValueFromParts(350, 900), "350");
});

test("portion picker rounds and bounds gram values", () => {
  assert.equal(portionFromValue("125,5"), 126);
  assert.equal(portionFromValue("0"), 1);
  assert.equal(portionFromValue("2500"), 2000);
  assert.equal(portionFromValue(""), 100);
});
