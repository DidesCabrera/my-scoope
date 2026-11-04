import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

import { nextExclusivePicker } from "../src/components/ui/exclusive-picker-state";

test("opening a picker replaces the previously expanded picker", () => {
  assert.equal(nextExclusivePicker("height", "weight", true), "weight");
  assert.equal(nextExclusivePicker("weight", "height", true), "height");
});

test("closing a picker only clears that picker", () => {
  assert.equal(nextExclusivePicker("height", "height", false), null);
  assert.equal(nextExclusivePicker("weight", "height", false), "weight");
});

test("onboarding controls height and weight as one exclusive picker group", async () => {
  const [journey, measurementField] = await Promise.all([
    readFile(path.resolve(process.cwd(), "src/components/onboarding/onboarding-journey-view.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/components/ui/native-measurement-field.native.tsx"), "utf8"),
  ]);

  assert.match(journey, /expanded=\{expandedMeasurement === "height"\}/);
  assert.match(journey, /expanded=\{expandedMeasurement === "weight"\}/);
  assert.match(journey, /nextExclusivePicker\(current, "height", expanded\)/);
  assert.match(journey, /nextExclusivePicker\(current, "weight", expanded\)/);
  assert.match(measurementField, /const visible = expanded \?\? internalExpanded/);
});

test("date and time fields support the same controlled expansion contract", async () => {
  const [dateTimeField, dateTimeTypes] = await Promise.all([
    readFile(path.resolve(process.cwd(), "src/components/ui/native-date-time-field.native.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/components/ui/native-date-time-field.types.ts"), "utf8"),
  ]);

  assert.match(dateTimeTypes, /expanded\?: boolean/);
  assert.match(dateTimeTypes, /onExpandedChange\?\(expanded: boolean\): void/);
  assert.match(dateTimeField, /const expanded = controlledExpanded \?\? internalExpanded/);
  assert.match(dateTimeField, /onExpandedChange\?\.\(nextExpanded\)/);
});

test("every audited multi-picker surface keeps one active picker", async () => {
  const [gallery, personalRecords, programActivation, weight] = await Promise.all([
    readFile(path.resolve(process.cwd(), "src/components/dev/wheel-picker-gallery.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/app/personal-records-edit.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/app/program/activate.tsx"), "utf8"),
    readFile(path.resolve(process.cwd(), "src/app/weight.tsx"), "utf8"),
  ]);

  assert.match(personalRecords, /expandedPicker === "birth-date"/);
  assert.match(personalRecords, /expandedPicker === "height"/);
  assert.match(programActivation, /expandedPicker === "start-date"/);
  assert.match(programActivation, /expandedPicker === "daily-time"/);
  assert.match(weight, /expandedPicker === "current-weight"/);
  assert.match(weight, /expandedPicker === "current-time"/);
  assert.match(weight, /expandedPicker === "history-weight"/);
  assert.match(weight, /expandedPicker === "history-date"/);
  assert.match(weight, /expandedPicker === "history-time"/);
  assert.match(weight, /function openCreate\(\) \{\s+setExpandedPicker\(null\)/);
  assert.match(weight, /function openEdit\(item: WeightItem\) \{\s+setExpandedPicker\(null\)/);
  assert.match(gallery, /const datePicker = `\$\{preview\.width\}:date`/);
  assert.match(gallery, /expandedPicker === weightPicker/);
});
