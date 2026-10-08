import { View } from "react-native";

import { PersonalRecordCard } from "@/components/profile";
import { InlineNotice, SectionTitle } from "@/components/ui";
import { tokens } from "@/design/tokens";

const examples = [
  { kind: "body" as const, items: [
    { key: "birth_date", label: "Fecha de nacimiento", value: "10 may 1990" },
    { key: "sex", label: "Sexo nutricional", value: "Femenino" },
    { key: "height_cm", label: "Altura", value: "172 cm" },
  ] },
  { kind: "planning" as const, items: [
    { key: "goal", label: "Objetivo nutricional", value: "Ganar masa muscular" },
    { key: "activity_level", label: "Actividad habitual", value: "Alta" },
    { key: "training_frequency", label: "Entrenamientos", value: "4 por semana" },
  ] },
  { kind: "preferences" as const, items: [
    { key: "dietary_pattern", label: "Patrón alimentario", value: "Omnívoro" },
    { key: "allergies_or_intolerances", label: "Alergias o intolerancias", value: "Lactosa" },
    { key: "avoided_foods", label: "Alimentos evitados", value: "Apio" },
  ] },
  { kind: "metrics" as const, items: [
    { key: "weight_kg", label: "Peso actual", value: "68,4 kg" },
    { key: "weight_date", label: "Última medición", value: "7 oct 2026" },
    { key: "weight_source", label: "Origen", value: "Registro manual" },
  ] },
];

export function PersonalRecordCardGallery() {
  return (
    <View style={{ gap: tokens.spacing.lg }}>
      <SectionTitle detail="Componentes compartidos por Fichas personales y el chat" title="Fichas personales" />
      <InlineNotice>Una misma fuente persistente alimenta la ficha visible, el contexto del asistente y la planificación nutricional.</InlineNotice>
      {examples.map((example) => <PersonalRecordCard items={example.items} key={example.kind} kind={example.kind} />)}
    </View>
  );
}
