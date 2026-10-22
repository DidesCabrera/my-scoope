import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { CommercialLimitContent, type CommercialLimitEntity } from "@/components/subscriptions/commercial-limit-sheet";
import { ScrollableTabBar } from "@/components/ui/tab-bars";
import { SectionTitle, textStyles } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";

const noop = () => undefined;

const limits: Record<CommercialLimitEntity, number> = {
  comparison: 0,
  dailyPlan: 4,
  meal: 12,
  program: 1,
};

export function SalesMomentsGallery() {
  const [entity, setEntity] = useState<CommercialLimitEntity>("dailyPlan");
  const limit = limits[entity];
  return (
    <View style={styles.gallery}>
      <SectionTitle
        detail="Componente productivo · sin compras, navegación ni cambios de plan"
        title="Instancias de venta"
      />
      <Text style={textStyles.muted}>
        Estados comerciales que aparecen cuando una intención válida supera los beneficios del plan actual.
        Cada vista debe explicar qué ocurrió, conservar el trabajo existente y ofrecer una salida clara.
      </Text>
      <ScrollableTabBar<CommercialLimitEntity>
        accessibilityLabel="Entidad con límite alcanzado"
        activeTab={entity}
        density="compact"
        onChange={setEntity}
        tabs={[
          { key: "dailyPlan", label: "Planes" },
          { key: "meal", label: "Comidas" },
          { key: "program", label: "Programas" },
          { key: "comparison", label: "Comparaciones" },
        ]}
      />
      <View style={styles.phonePreview}>
        <Text style={styles.previewLabel}>ESCENARIO 01 · LÍMITE DE LIBRERÍA</Text>
        <CommercialLimitContent entity={entity} limit={limit} onClose={noop} onUpgrade={noop} planName="Free" used={limit} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  gallery: { gap: tokens.spacing.md },
  phonePreview: { alignSelf: "center", gap: tokens.spacing.sm, maxWidth: 414, width: "100%" },
  previewLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0.8, paddingHorizontal: tokens.spacing.xs },
});
