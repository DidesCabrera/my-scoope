import assert from "node:assert/strict";
import { createRequire } from "node:module";
import test from "node:test";

const requireMobile = createRequire(import.meta.url);
const braces = requireMobile("braces") as {
  (input: string, options?: { expand?: boolean }): string[];
  compile(input: string | object): string;
  expand(input: string | object): string[];
  parse(input: string): object;
  stringify(input: string | object): string;
};

test("the patched brace parser bounds deeply nested patterns without changing normal globs", () => {
  assert.deepEqual(braces("src/{app,components}/*.tsx"), ["src/(app|components)/*.tsx"]);
  assert.deepEqual(braces("{a,b}", { expand: true }), ["a", "b"]);
  const nested = "{".repeat(80) + "a,b" + "}".repeat(80);
  for (const operation of [
    () => braces.parse(nested),
    () => braces.compile(nested),
    () => braces.expand(nested),
    () => braces.stringify(nested),
  ]) {
    assert.throws(operation, { name: "SyntaxError", message: "Brace pattern exceeds maximum nesting depth" });
  }
});

test("direct AST walkers reject excessive depth without a call stack overflow", () => {
  const ast: { type: string; nodes: unknown[] } = { type: "root", nodes: [] };
  let parent = ast;
  for (let index = 0; index < 80; index++) {
    const child = { type: "brace", open: true, close: true, commas: 1, nodes: [] as unknown[], parent };
    parent.nodes.push(child);
    parent = child;
  }
  parent.nodes.push({ type: "text", value: "a" });
  for (const operation of [
    () => braces.compile(ast),
    () => braces.expand(ast),
    () => braces.stringify(ast),
  ]) {
    assert.throws(operation, { name: "SyntaxError", message: "Brace pattern exceeds maximum nesting depth" });
  }
});
