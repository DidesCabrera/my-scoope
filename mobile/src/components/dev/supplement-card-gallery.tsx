import { SectionTitle, SupplementCard } from "@/components/ui";

export function SupplementCardGallery() {
  return (
    <>
      <SectionTitle detail="Biblioteca y composición editable" title="Card de suplemento" />
      <SupplementCard
        brand="FNL"
        componentCount={2}
        name="Multivitamínico diario"
        onOpen={() => undefined}
        quantity="1"
        unit="capsule"
      />
    </>
  );
}
