import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

async function source(relativePath: string) {
  return readFile(path.resolve(process.cwd(), relativePath), "utf8");
}

test("calendar opens the commitment registry before registration", async () => {
  const calendar = await source("src/components/calendarization/calendar-overview-screen.tsx");
  assert.match(calendar, /label="Ver registro de compromisos"[\s\S]*router\.push\("\/calendar\/registry"/);
  assert.doesNotMatch(calendar, /setCommitmentMenuVisible/);
});

test("commitment registry uses the canonical commitment presentation", async () => {
  const [registry, commitments] = await Promise.all([
    source("src/app/calendar/registry.tsx"),
    source("src/components/calendarization/calendar-commitments.ts"),
  ]);

  assert.match(commitments, /shopping: \{ label: "Hacer compras"[^\n]*icon: ShoppingBasket/);
  assert.match(commitments, /cooking: \{ label: "Cocinar"[^\n]*icon: CookingPot/);
  assert.match(commitments, /training: \{ label: "Entrenar"[^\n]*icon: Dumbbell/);
  assert.match(commitments, /nutritionist: \{ label: "Cita nutricionista"[^\n]*icon: Stethoscope/);
  assert.match(registry, /commitmentKinds\.map[\s\S]*presentation\.icon/);
  assert.match(registry, /label: "Todos"/);
  assert.match(registry, /nutritionist: "Cita nutri\."/);
  assert.match(registry, /<ScrollableTabBar<CommitmentScope>/);
  assert.match(registry, /secondaryAction: \{ icon: "plus", label: "Registrar un compromiso"/);
  assert.match(registry, /action: \{ icon: "more", label: "Más opciones de compromisos"/);
  assert.match(registry, /Configurar notificaciones de compromisos/);
  assert.match(registry, /fallback: "\/calendar"/);
  assert.match(registry, /mode: "back"/);
  assert.doesNotMatch(registry, /styles\.addButton/);
  assert.match(registry, /<View style=\{styles\.calendarSection\}>[\s\S]*styles\.monthNavigation[\s\S]*styles\.grid/);
  assert.doesNotMatch(registry, /<Card>[\s\S]*styles\.monthNavigation[\s\S]*styles\.grid/);
  assert.match(registry, /commitments\.map/);
  assert.match(registry, /<ActionSheetAction icon=\{commitmentPresentation\[kind\]\.icon\}/);
});
