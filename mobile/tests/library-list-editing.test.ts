import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

test("library list actions expose one unified editing flow", async () => {
  const actions = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-actions.tsx"), "utf8");
  const screen = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-screen.tsx"), "utf8");

  assert.match(actions, /label: "Editar lista"/);
  assert.doesNotMatch(actions, /label: "Reordenar"|label: "Eliminar"/);
  assert.match(screen, /^(?=[\s\S]*mode.*"list" \| "edit")(?=[\s\S]*icon: "more")(?=[\s\S]*label: `Acciones de \$\{title\}`)(?=[\s\S]*label: "Listo")(?=[\s\S]*label: "Cancelar")(?=[\s\S]*label: "Eliminar")/);
  assert.match(screen, /food: "Eliminar alimentos"[\s\S]*program: "Eliminar programas"[\s\S]*item_ids: itemIds/);
  assert.match(screen, /<LibraryListEditor[\s\S]*onDelete=\{confirmDeleteItem\}[\s\S]*onReorder=\{saveOrder\}[\s\S]*onToggle=\{toggleSelected\}[\s\S]*selectedIds=\{selectedIds\}/);
});

test("the library list editor uses the UI-system drag and delete table pattern", async () => {
  const editor = await readFile(path.resolve(process.cwd(), "src/components/libraries/library-list-editor.tsx"), "utf8");

  assert.match(editor, /NestableDraggableFlatList[\s\S]*ScaleDecorator[\s\S]*GripVertical/);
  assert.match(editor, /accessibilityRole="checkbox"[\s\S]*accessibilityState=\{\{ checked: selectedIds\.has\(item\.id\), disabled: busy \}\}/);
  assert.match(editor, /accessibilityLabel=\{`Eliminar \$\{item\.name\}`\}[\s\S]*<Trash2 color=\{tokens\.color\.danger\}/);
  assert.match(editor, /checkboxButtonSelected: \{ backgroundColor: tokens\.color\.surfaceMuted, borderColor: tokens\.color\.danger \}/);
  assert.match(editor, /Mantén pulsado y arrastra para cambiar la posición[\s\S]*Seleccionar.*item\.name.*para eliminar/);
  assert.match(editor, /onDragEnd=\{\(\{ data, from, to \}\)/);
  assert.doesNotMatch(editor, />Elementos<|>Acciones</);
  assert.match(editor, /table: \{ borderBottomColor:[^}]*borderBottomWidth: 1[^}]*borderRadius: 0[^}]*borderTopWidth: 1[^}]*marginHorizontal: -tokens\.spacing\.screen/);
});
