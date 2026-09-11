import type { Href } from "expo-router";

type SearchParam = string | string[] | undefined;

export function internalHref(value: SearchParam): Href | undefined {
  const candidate = Array.isArray(value) ? value[0] : value;
  if (!candidate || !candidate.startsWith("/") || candidate.startsWith("//") || candidate.includes("\\")) return undefined;
  return candidate as Href;
}
