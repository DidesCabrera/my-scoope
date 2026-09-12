import type { Href } from "expo-router";

export type ProductAreaKey = "home" | "program" | "assistant" | "comparator" | "inbox";

type ProductAreaBase = {
  key: ProductAreaKey;
  label: string;
};

export type AvailableProductArea = ProductAreaBase & {
  availability: "available";
  href: Href;
};

export type PlannedProductArea = ProductAreaBase & {
  availability: "planned";
};

export type ProductArea = AvailableProductArea | PlannedProductArea;

export const productAreas: readonly ProductArea[] = [
  { availability: "available", href: "/today", key: "home", label: "Inicio" },
  { availability: "available", href: "/program" as Href, key: "program", label: "Mi programa activo" },
  { availability: "available", href: "/assistant" as Href, key: "assistant", label: "Asistente AI" },
  { availability: "available", href: "/comparator" as Href, key: "comparator", label: "Comparador" },
  { availability: "available", href: "/inbox" as Href, key: "inbox", label: "Inbox" },
];

export function listAvailableProductAreas(): AvailableProductArea[] {
  return productAreas.filter((area): area is AvailableProductArea => area.availability === "available");
}
