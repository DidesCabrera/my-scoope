import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const gallery = readFileSync(new URL("../src/components/dev/sales-moments-gallery.tsx", import.meta.url), "utf8");
const navigation = readFileSync(new URL("../src/components/dev/gallery-navigation.tsx", import.meta.url), "utf8");
const uiGallery = readFileSync(new URL("../src/app/dev/ui-gallery.tsx", import.meta.url), "utf8");
const limitSheet = readFileSync(new URL("../src/components/subscriptions/commercial-limit-sheet.tsx", import.meta.url), "utf8");

test("the UI gallery reserves a sales moments section", () => {
  assert.match(navigation, /salesMoments.*Instancias de venta/);
  assert.match(uiGallery, /tab === "salesMoments".*<SalesMomentsGallery/);
});

test("the sales moment preserves the approved commercial limit design", () => {
  assert.match(gallery, /<CommercialLimitContent/);
  assert.match(gallery, /dailyPlan: 4/);
  assert.match(gallery, /comparison: 0/);
  assert.match(gallery, /key: "comparison", label: "Comparaciones"/);
  assert.match(limitSheet, /Guarda comparaciones en tu librería/);
  assert.match(limitSheet, /usageLabel: "Comparaciones guardadas"/);
  assert.match(limitSheet, /Agrega más planes a tu librería/);
  assert.match(limitSheet, /usageLabel: "Planes utilizados"/);
  assert.match(limitSheet, /marginHorizontal: -6/);
  assert.match(limitSheet, /<EntityIcon entity=\{entity\} size="regular" \/>/);
  assert.match(limitSheet, /progressSpacing: \{ marginBottom: 8, marginTop: 8 \}/);
  assert.match(limitSheet, /usageHeader: \{[^}]*marginTop: 4/);
  assert.doesNotMatch(limitSheet, /borderTopWidth: 4/);
  assert.match(limitSheet, /<Card accent=\{tokens\.color\.carbs\}/);
  assert.match(limitSheet, /style=\{\[styles\.usagePanel, \{ borderTopColor: accent \}\]\}/);
  assert.match(limitSheet, /usagePanel: \{[^}]*borderRadius: tokens\.radius\.lg[^}]*borderTopWidth: 3/);
  assert.match(limitSheet, /Planes Basic y Pro ilimitados/);
  assert.match(limitSheet, /<MyScoopeBrandLogo commercial \/>/);
  assert.match(limitSheet, /brandLogo: \{ alignItems: "center", marginBottom: 6 \}/);
  assert.match(limitSheet, /copy: \{ alignItems: "center"/);
  assert.match(limitSheet, /subtitle: \{ textAlign: "center" \}/);
  assert.match(limitSheet, /planes <Text style=\{styles\.planNameEmphasis\}>Basic<\/Text> y <Text style=\{styles\.planNameEmphasis\}>Pro<\/Text>/);
  assert.match(limitSheet, /planNameEmphasis: \{ fontWeight: tokens\.weight\.extraBold \}/);
  assert.doesNotMatch(limitSheet, /no realizamos ningún cambio/);
});
