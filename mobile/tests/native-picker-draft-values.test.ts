import assert from "node:assert/strict";
import test from "node:test";

import {
  committedDateTimeDraft,
  dateTimeDraftFromDate,
  type DateTimeDraft,
} from "../src/components/ui/native-picker-draft-values";

const minimum = new Date(2020, 0, 1);
const maximum = new Date(2030, 11, 31);

function draft(overrides: Partial<DateTimeDraft> = {}): DateTimeDraft {
  return { day: 1, hour: 0, minute: 0, month: 0, year: 2026, ...overrides };
}

test("date picker drafts preserve every visible wheel part", () => {
  const value = new Date(2026, 9, 21, 16, 45);

  assert.deepEqual(dateTimeDraftFromDate(value), {
    day: 21,
    hour: 16,
    minute: 45,
    month: 9,
    year: 2026,
  });
});

test("date commits clamp a stable 31-day wheel to the selected month", () => {
  const regularFebruary = committedDateTimeDraft(
    draft({ day: 31, month: 1, year: 2025 }),
    "date",
    new Date(2025, 0, 1),
    minimum,
    maximum,
  );
  const leapFebruary = committedDateTimeDraft(
    draft({ day: 31, month: 1, year: 2024 }),
    "date",
    new Date(2024, 0, 1),
    minimum,
    maximum,
  );

  assert.equal(regularFebruary.getDate(), 28);
  assert.equal(leapFebruary.getDate(), 29);
});

test("date and time commits respect bounds and preserve the base day", () => {
  const bounded = committedDateTimeDraft(
    draft({ day: 31, month: 11, year: 2035 }),
    "date",
    new Date(2026, 0, 1),
    minimum,
    maximum,
  );
  const time = committedDateTimeDraft(
    draft({ hour: 18, minute: 35 }),
    "time",
    new Date(2026, 9, 21, 8, 0),
    minimum,
    maximum,
  );

  assert.equal(bounded.getTime(), maximum.getTime());
  assert.equal(time.getDate(), 21);
  assert.equal(time.getHours(), 18);
  assert.equal(time.getMinutes(), 35);
});
