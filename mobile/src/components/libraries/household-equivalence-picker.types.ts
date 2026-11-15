export type HouseholdMeasure = "" | "unit" | "cup" | "tablespoon" | "scoop" | "other" | "slice" | "can" | "fillet" | "leaf" | "strip" | "g" | "ml";

export const householdMeasures: { value: HouseholdMeasure; label: string }[] = [
  { value: "", label: "Ninguna" }, { value: "unit", label: "Unidad" }, { value: "cup", label: "Taza" },
  { value: "tablespoon", label: "Cucharada" }, { value: "scoop", label: "Scoop" }, { value: "other", label: "Otra" },
  { value: "slice", label: "Rodaja" }, { value: "can", label: "Lata" }, { value: "fillet", label: "Filete" },
  { value: "leaf", label: "Hoja" }, { value: "strip", label: "Tira" }, { value: "g", label: "Gramo" }, { value: "ml", label: "Mililitro" },
];

export const householdAmounts = [
  ...Array.from({ length: 80 }, (_, index) => (index + 1) / 4),
  ...Array.from({ length: 80 }, (_, index) => index + 21),
];

export type HouseholdEquivalencePickerProps = {
  amount: string;
  measure: HouseholdMeasure;
  onAmountChange(amount: string): void;
  onMeasureChange(measure: HouseholdMeasure): void;
};
