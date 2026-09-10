import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const sourceCache = new Map<string, Promise<string>>();

export function readTestFile(file: string, encoding: BufferEncoding): Promise<string> {
  const key = `${encoding}:${file}`;
  const cached = sourceCache.get(key);
  if (cached) return cached;

  const pending = readFile(file, encoding);
  sourceCache.set(key, pending);
  return pending;
}

export function assertSourceMatch(source: string, pattern: RegExp, message?: string): void {
  assert.match(source, pattern, message ?? `Expected source to match ${pattern}`);
}

export function assertSourceDoesNotMatch(source: string, pattern: RegExp, message?: string): void {
  assert.doesNotMatch(source, pattern, message ?? `Expected source not to match ${pattern}`);
}
