import contract from "./tokens.json";

export const tokens = contract;
export type VisualTokens = typeof tokens;

export const font = {
  regular: "System",
  medium: "System",
  semibold: "System",
  bold: "System",
} as const;
