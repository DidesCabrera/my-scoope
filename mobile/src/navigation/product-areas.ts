import type { Href } from "expo-router";

export type ProductAreaKey = "home" | "calendar" | "assistant" | "comparator" | "inbox";

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
  { availability: "available", href: "/calendar" as Href, key: "calendar", label: "Mi calendario" },
  { availability: "available", href: "/comparator" as Href, key: "comparator", label: "Comparaciones" },
  { availability: "available", href: "/inbox" as Href, key: "inbox", label: "Compartidos" },
  { availability: "available", href: "/assistant" as Href, key: "assistant", label: "Asistente Nutricional" },
];

export function listAvailableProductAreas(): AvailableProductArea[] {
  return productAreas.filter((area): area is AvailableProductArea => area.availability === "available");
}
