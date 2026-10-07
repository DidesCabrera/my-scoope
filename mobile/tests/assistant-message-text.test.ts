import assert from "node:assert/strict";
import test from "node:test";

import { parseAssistantText } from "../src/components/assistant/assistant-message-parser";

test("assistant text preserves prose while recognizing visual markdown blocks", () => {
  const source = "# Resumen\n\nTexto con **énfasis**.\n\n- Primero\n- Segundo\n\n1. Revisar\n2. Confirmar\n\n> Nota importante";

  assert.deepEqual(parseAssistantText(source), [
    { kind: "heading", level: 1, text: "Resumen" },
    { kind: "paragraph", text: "Texto con **énfasis**." },
    { kind: "unordered-item", text: "Primero" },
    { kind: "unordered-item", text: "Segundo" },
    { kind: "ordered-item", number: "1", text: "Revisar" },
    { kind: "ordered-item", number: "2", text: "Confirmar" },
    { kind: "quote", text: "Nota importante" },
  ]);
});

test("plain assistant prose is not rewritten", () => {
  const source = "Mantengo esta respuesta tal como fue generada.\nLa segunda línea sigue intacta.";

  assert.deepEqual(parseAssistantText(source), [{ kind: "paragraph", text: source }]);
});
