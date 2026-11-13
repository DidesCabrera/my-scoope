import assert from "node:assert/strict";
import test from "node:test";

import { normalizeFoodVisualName, parseFoodVisualManifest } from "../src/components/nutrition/remote-food-visuals-core";

const digest = "a".repeat(64);
const ref = "93532264-f548-4f81-a0ae-a317015bb6d4";

test("remote food visual names match localized accents and whitespace", () => {
  assert.equal(normalizeFoodVisualName("  Hígado   de Pollo "), "higado de pollo");
});

test("remote manifest accepts only same-server versioned image paths", () => {
  const path = `/api/v1/foods/visual-assets/${ref}/${digest}.png`;
  const images = parseFoodVisualManifest({ images: {
    "Hígado de pollo": path,
    "Imagen externa": "https://untrusted.example/icon.png",
    "Otra ruta": "/admin/logout/",
  }, food_ids: { "42": path, "not-an-id": path } }, "https://www.myscoope.com");
  assert.equal(images.get("name:higado de pollo"), `https://www.myscoope.com${path}`);
  assert.equal(images.get("id:42"), `https://www.myscoope.com${path}`);
  assert.equal(images.size, 2);
});
