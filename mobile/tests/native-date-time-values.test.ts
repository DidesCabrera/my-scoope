import assert from "node:assert/strict";
import test from "node:test";

import { pickerDateFromValue, pickerValueFromDate } from "../src/components/ui/native-date-time-values";
import { localDateValue } from "../src/presentation/date-time-values";

test("native picker values preserve local calendar dates without UTC shifts", () => {
  const selected = pickerDateFromValue("2026-10-07", "date");

  assert.equal(selected.getFullYear(), 2026);
  assert.equal(selected.getMonth(), 9);
  assert.equal(selected.getDate(), 7);
  assert.equal(pickerValueFromDate(selected, "date"), "2026-10-07");
  assert.equal(localDateValue(selected), "2026-10-07");
});

test("native picker values preserve the API 24-hour time contract", () => {
  const fallback = new Date(2026, 9, 7, 12, 0);
  const selected = pickerDateFromValue("07:05", "time", fallback);

  assert.equal(selected.getHours(), 7);
  assert.equal(selected.getMinutes(), 5);
  assert.equal(pickerValueFromDate(selected, "time"), "07:05");
});
