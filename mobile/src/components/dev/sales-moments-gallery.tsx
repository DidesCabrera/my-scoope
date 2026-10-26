import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { CommercialLimitContent, SharedImportLimitContent, type CommercialLimitEntity } from "@/components/subscriptions/commercial-limit-sheet";
import { ScrollableTabBar } from "@/components/ui/tab-bars";
import { SectionTitle, textStyles } from "@/components/ui/typography";
import { tokens } from "@/design/tokens";

const noop = () => undefined;
type LimitScenario = CommercialLimitEntity | "receivedImports";

const limits: Record<CommercialLimitEntity, number> = {
  comparison: 0,
  dailyPlan: 4,
  meal: 12,
  program: 1,
};

export function SalesMomentsGallery() {
  const [scenario, setScenario] = useState<LimitScenario>("dailyPlan");
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
      <ScrollableTabBar<LimitScenario>
        accessibilityLabel="Escenario con límite alcanzado"
        activeTab={scenario}
        density="compact"
        onChange={setScenario}
        tabs={[
          { key: "dailyPlan", label: "Planes" },
          { key: "meal", label: "Comidas" },
          { key: "program", label: "Programas" },
          { key: "comparison", label: "Comparaciones" },
          { key: "receivedImports", label: "Recibidos" },
        ]}
      />
      <View style={styles.phonePreview}>
        <Text style={styles.previewLabel}>{scenario === "receivedImports" ? "ESCENARIO 02 · RECIBIDOS AGREGADOS A LA LIBRERÍA" : "ESCENARIO 01 · LÍMITE DE LIBRERÍA"}</Text>
        {scenario === "receivedImports" ? <SharedImportLimitContent limit={1} onClose={noop} onUpgrade={noop} planName="Free" used={1} /> : (
          <CommercialLimitContent entity={scenario} limit={limits[scenario]} onClose={noop} onUpgrade={noop} planName="Free" used={limits[scenario]} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  gallery: { gap: tokens.spacing.md },
  phonePreview: { alignSelf: "center", gap: tokens.spacing.sm, maxWidth: 414, width: "100%" },
  previewLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.weight.bold, letterSpacing: 0.8, paddingHorizontal: tokens.spacing.xs },
});
