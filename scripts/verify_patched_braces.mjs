import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const patchPath = path.join(root, "mobile/patches/braces+3.0.3.patch");
const expectedPatchSha256 = "f5ca0628e51a6e5dfa5b84c7827444b40bf406c653d53db32e011a0b45140e62";
const requireMobile = createRequire(path.join(root, "mobile/package.json"));

export const PATCHED_BRACES_ADVISORY_SOURCE = 1240992;

export function verifyPatchedBraces() {
  const patchHash = createHash("sha256").update(readFileSync(patchPath)).digest("hex");
  assert.equal(patchHash, expectedPatchSha256, "The reviewed braces patch has changed");
  assert.equal(requireMobile("braces/package.json").version, "3.0.3");

  const braces = requireMobile("braces");
  const tooDeep = "{".repeat(80) + "a,b" + "}".repeat(80);
  const tooManyParens = "(".repeat(80) + "a" + ")".repeat(80);
  const depthError = (error) => error instanceof SyntaxError && error.message === "Brace pattern exceeds maximum nesting depth";

  assert.deepEqual(braces("src/{app,components}/*.tsx"), ["src/(app|components)/*.tsx"]);
  assert.deepEqual(braces("{a,b}", { expand: true }), ["a", "b"]);
  for (const operation of [
    () => braces.parse(tooDeep),
    () => braces.compile(tooDeep),
    () => braces.expand(tooDeep),
    () => braces.stringify(tooDeep),
    () => braces.compile(tooManyParens),
  ]) {
    assert.throws(operation, depthError);
  }

  const nestedAst = { type: "root", nodes: [] };
  let node = nestedAst;
  for (let index = 0; index < 80; index++) {
    const child = { type: "brace", open: true, close: true, commas: 1, nodes: [], parent: node };
    node.nodes.push(child);
    node = child;
  }
  node.nodes.push({ type: "text", value: "a" });
  for (const operation of [
    () => braces.compile(nestedAst),
    () => braces.expand(nestedAst),
    () => braces.stringify(nestedAst),
  ]) {
    assert.throws(operation, depthError);
  }
}
