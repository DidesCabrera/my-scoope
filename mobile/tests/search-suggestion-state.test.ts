import assert from "node:assert/strict";
import test from "node:test";

import { visibleSearchSuggestions } from "../src/components/ui/search-suggestion-state";

const result = { search: "avena", items: [{ id: 1, name: "Avena" }] };

test("suggestions remain visible only for the current unsubmitted search", () => {
  assert.deepEqual(visibleSearchSuggestions(result, " avena ", ""), result.items);
  assert.deepEqual(visibleSearchSuggestions(result, "arroz", ""), []);
  assert.deepEqual(visibleSearchSuggestions(result, "avena", "avena"), []);
  assert.deepEqual(visibleSearchSuggestions(result, "", ""), []);
});
