import { SavedComparisonListCard } from "@/components/comparisons";
import { SectionTitle } from "@/components/ui";

const savedFoodComparison = {
  id: 1,
  item_count: 2,
  items: [
    { id: 1, name: "Yogur griego natural", position: 1, quantity: 100, values: { calories: 97, carbs_g: 3.8, fat_g: 5, protein_g: 9, protein_per_kilogram: null } },
    { id: 2, name: "Skyr natural", position: 2, quantity: 100, values: { calories: 62, carbs_g: 4, fat_g: 0.2, protein_g: 12, protein_per_kilogram: null } },
  ],
  kind: "foods" as const,
  kind_label: "Alimentos",
  name: "Yogures altos en proteína",
  updated_at: "2026-10-07T20:00:00-03:00",
};

export function SavedComparisonCardGallery() {
  return (
    <>
      <SectionTitle detail="Card compartida por Comparaciones y el chat" title="Comparación guardada" />
      <SavedComparisonListCard item={savedFoodComparison} onPress={() => undefined} />
    </>
  );
}
