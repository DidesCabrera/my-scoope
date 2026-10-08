import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("the UI gallery exposes native wheel selectors at representative compact widths", async () => {
  const [dateTimeField, gallery, measurementField, navigation, wheelGallery] = await Promise.all([
    source("src/components/ui/native-date-time-field.native.tsx"),
    source("src/app/dev/ui-gallery.tsx"),
    source("src/components/ui/native-measurement-field.native.tsx"),
    source("src/components/dev/gallery-navigation.tsx"),
    source("src/components/dev/wheel-picker-gallery.tsx"),
  ]);

  assert.match(navigation, /key: "selectors", label: "Selectores"/);
  assert.match(gallery, /tab === "selectors"/);
  assert.match(gallery, /<WheelPickerGallery \/>/);
  assert.match(wheelGallery, /width: 402/);
  assert.match(wheelGallery, /width: 375/);
  assert.match(wheelGallery, /width: 320/);
  assert.match(wheelGallery, /<NativeDateTimeField/);
  assert.match(wheelGallery, /kind="height"/);
  assert.match(wheelGallery, /kind="weight"/);
  assert.match(dateTimeField, /dateDayPicker: \{ height: nativeWheelMetrics\.height, width: 90 \}/);
  assert.match(dateTimeField, /dateMonthPicker: \{ height: nativeWheelMetrics\.height, marginLeft: -8, width: 104 \}/);
  assert.match(dateTimeField, /dateYearPicker: \{ height: nativeWheelMetrics\.height, marginLeft: -8, width: 104 \}/);
  assert.match(dateTimeField, /<NativeWheelAdornment label=":" width=\{8\} \/>/);
  assert.match(measurementField, /weightKilogramsPickerColumn: \{ flex: 0, width: 96 \}/);
  assert.match(measurementField, /weightGramsPickerColumn: \{ flex: 0, width: 80 \}/);
  assert.match(measurementField, /<NativeWheelAdornment label="," width=\{8\} \/>/);
});
