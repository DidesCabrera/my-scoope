import path from "node:path";
import test from "node:test";

import { assertSourceMatch, readTestFile } from "./support/source-contract";

test("Explore meals uses the curated endpoint and editorial filters", async () => {
  const screen = await readTestFile(path.resolve(process.cwd(), "src/components/explore/explore-meals-screen.tsx"), "utf8");

  assertSourceMatch(screen, /\/api\/v1\/explore\/meals\?/);
  assertSourceMatch(screen, /Filtrar por ocasión/);
  assertSourceMatch(screen, /Filtrar por estilo alimentario/);
  assertSourceMatch(screen, /Desayuno[\s\S]*Almuerzo[\s\S]*Cena[\s\S]*Colación[\s\S]*Pre-entreno[\s\S]*Post-entreno/);
  assertSourceMatch(screen, /Omnívoras[\s\S]*Pescetarianas[\s\S]*Vegetarianas[\s\S]*Veganas/);
});

test("Explore cards place save-to-library beside detail navigation", async () => {
  const card = await readTestFile(path.resolve(process.cwd(), "src/components/libraries/library-card.tsx"), "utf8");
  const screen = await readTestFile(path.resolve(process.cwd(), "src/components/explore/explore-meals-screen.tsx"), "utf8");

  assertSourceMatch(card, /onSaveToLibrary[\s\S]*BookmarkPlus[\s\S]*ChevronRight/);
  assertSourceMatch(card, /Guardar \$\{item\.name\} en mi biblioteca/);
  assertSourceMatch(screen, /\/api\/v1\/explore\/meals\/\$\{item\.catalog_id\}\/save/);
  assertSourceMatch(screen, /savedToLibrary=\{item\.is_saved\}/);
  assertSourceMatch(screen, /detailHref=\{`\/explore\/meals\/\$\{item\.catalog_id\}` as Href\}/);
});

test("Explore detail remains read-only and offers a personal library destination after saving", async () => {
  const detail = await readTestFile(path.resolve(process.cwd(), "src/components/explore/explore-meal-detail-screen.tsx"), "utf8");

  assertSourceMatch(detail, /interactive=\{false\}/);
  assertSourceMatch(detail, /navigable=\{false\}/);
  assertSourceMatch(detail, /Abrir Mis Comidas/);
  assertSourceMatch(detail, /\/api\/v1\/explore\/meals\/\$\{item\.catalog_id\}\/save/);
});
