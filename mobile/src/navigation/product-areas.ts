import type { Href } from "expo-router";

export type ProductAreaKey = "home" | "program" | "assistant" | "proposals" | "comparator";

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
  { availability: "available", href: "/program" as Href, key: "program", label: "Mi programa" },
  { availability: "available", href: "/assistant" as Href, key: "assistant", label: "Asistente" },
  { availability: "available", href: "/proposals" as Href, key: "proposals", label: "Propuestas" },
  { availability: "available", href: "/comparator" as Href, key: "comparator", label: "Comparador" },
];

export function listAvailableProductAreas(): AvailableProductArea[] {
  return productAreas.filter((area): area is AvailableProductArea => area.availability === "available");
}
