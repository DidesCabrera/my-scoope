import { useFocusEffect, usePathname, useRouter } from "expo-router";
import * as Crypto from "expo-crypto";
import { Check, ChevronRight, Clock, Pencil, PillBottle, Trash2 } from "lucide-react-native";
import { useCallback, useState } from "react";
import { Alert, Pressable, StyleSheet, Text, View } from "react-native";

import { userFacingError } from "@/api/errors";
import type { SupplementIntake } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { CalendarizedEntityActions } from "@/components/calendarization/calendarized-entity-actions";
import { ComparisonPanelGestureRows } from "@/components/libraries/comparison-panel-gesture-rows";
import { PanelEmptyState, PanelSurface } from "@/components/panels/panel-surface";
import { Button, EntityIcon, InlineNotice } from "@/components/ui";
import { tokens } from "@/design/tokens";
import { runGuardedNavigation } from "@/navigation/navigation-press-guard";

type IntakePage = { items: SupplementIntake[] };

const unitLabels: Record<string, { plural?: string; singular: string }> = {
  capsule: { plural: "cápsulas", singular: "cápsula" },
  drop: { plural: "gotas", singular: "gota" },
  g: { singular: "g" },
  gummy: { plural: "gomitas", singular: "gomita" },
  iu: { singular: "UI" },
  mcg: { singular: "mcg" },
  mg: { singular: "mg" },
  ml: { singular: "ml" },
  sachet: { plural: "sobres", singular: "sobre" },
  scoop: { plural: "medidas", singular: "medida" },
  softgel: { plural: "cápsulas blandas", singular: "cápsula blanda" },
  tablet: { plural: "comprimidos", singular: "comprimido" },
  tsp: { plural: "cucharaditas", singular: "cucharadita" },
};

function doseLabel(quantityValue: string, unitValue: string) {
  const quantity = Number(quantityValue);
  const formatted = Number.isFinite(quantity)
    ? quantity.toLocaleString("es-CL", { maximumFractionDigits: 3 })
    : quantityValue;
  const labels = unitLabels[unitValue];
  const unit = labels
    ? quantity === 1 ? labels.singular : labels.plural ?? labels.singular
    : unitValue;
  return `${formatted} ${unit}`;
}

export function SupplementIntakePanel({
  calendarizedDayId,
  completionEndpoint,
  dailyPlanId,
  editable = false,
  intakes,
  onChange,
  pinned = false,
}: {
  calendarizedDayId?: number;
  completionEndpoint?: string;
  dailyPlanId: number;
  editable?: boolean;
  intakes: SupplementIntake[];
  onChange?: (intakes: SupplementIntake[]) => void;
  pinned?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { apiRequest } = useSession();
  const [rows, setRows] = useState(intakes);
  const [error, setError] = useState<string | null>(null);
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [timeChangeIntake, setTimeChangeIntake] = useState<SupplementIntake | null>(null);
  const canMutateOrder = editable || calendarizedDayId != null;
  const canAdd = editable || calendarizedDayId != null || pinned;

  const publish = useCallback((items: SupplementIntake[]) => {
    setRows(items);
    onChange?.(items);
  }, [onChange]);

  useFocusEffect(useCallback(() => {
    let active = true;
    const endpoint = completionEndpoint ?? `/api/v1/library/daily-plans/${dailyPlanId}/supplement-intakes`;
    void apiRequest<IntakePage>(endpoint).then((page) => { if (active) { publish(page.items); setError(null); } }).catch((nextError) => { if (active) { setRows([]); setError(userFacingError(nextError)); } });
    return () => { active = false; };
  }, [apiRequest, completionEndpoint, dailyPlanId, publish]));

  async function toggle(intake: SupplementIntake) {
    if (!completionEndpoint) return;
    setSavingKey(intake.key);
    setError(null);
    try {
      const next = await apiRequest<IntakePage>(`${completionEndpoint}/${intake.id}/check-ins`, {
        method: "POST",
        body: JSON.stringify({ action: intake.status === "completed" ? "skipped" : "completed", idempotency_key: Crypto.randomUUID() }),
      });
      publish(next.items);
    } catch (nextError) { setError(userFacingError(nextError)); }
    finally { setSavingKey(null); }
  }

  async function reorder(nextOrder: SupplementIntake[]) {
    const previous = rows;
    publish(nextOrder);
    setSavingKey("order"); setError(null);
    try {
      const endpoint = calendarizedDayId != null
        ? `/api/v1/days/${calendarizedDayId}/supplement-intakes/order`
        : `/api/v1/library/daily-plans/${dailyPlanId}/supplement-intakes/order`;
      const next = await apiRequest<IntakePage>(endpoint, {
        method: "PUT",
        body: JSON.stringify(calendarizedDayId != null
          ? { ordered_keys: nextOrder.map((row) => row.key) }
          : { ordered_ids: nextOrder.map((row) => row.id) }),
      });
      publish(next.items);
    } catch (nextError) { publish(previous); setError(userFacingError(nextError)); throw nextError; }
    finally { setSavingKey(null); }
  }

  async function changeTime(intake: SupplementIntake, hour: string) {
    setSavingKey(intake.key); setError(null);
    try {
      const endpoint = calendarizedDayId != null
        ? `/api/v1/days/${calendarizedDayId}/supplement-intakes/${intake.id}/hour`
        : `/api/v1/library/daily-plans/${dailyPlanId}/supplement-intakes/${intake.id}`;
      const next = await apiRequest<IntakePage>(endpoint, {
        method: calendarizedDayId != null ? "PATCH" : "PUT",
        body: JSON.stringify(calendarizedDayId != null ? { hour } : {
          hour,
          items: intake.items.map((item) => ({ item_id: item.id, supplement_id: item.supplement_id, quantity: item.quantity, unit: item.unit })),
        }),
      });
      publish(next.items);
    } catch (nextError) { setError(userFacingError(nextError)); throw nextError; }
    finally { setSavingKey(null); }
  }

  function remove(intake: SupplementIntake) {
    Alert.alert("Eliminar ingesta", `¿Eliminar ${intake.label} de esta minuta diaria?`, [
      { text: "Cancelar", style: "cancel" },
      { text: "Eliminar", style: "destructive", onPress: () => {
        const endpoint = calendarizedDayId != null
          ? `/api/v1/days/${calendarizedDayId}/supplement-intakes/${intake.id}`
          : `/api/v1/library/daily-plans/${dailyPlanId}/supplement-intakes/${intake.id}`;
        setSavingKey(intake.key); setError(null);
        void apiRequest<IntakePage>(endpoint, { method: "DELETE" })
          .then((next) => publish(next.items))
          .catch((nextError) => setError(userFacingError(nextError)))
          .finally(() => setSavingKey(null));
      } },
    ]);
  }

  const openDetail = (intake: SupplementIntake) => {
    if (dailyPlanId > 0) router.push({
      pathname: "/libraries/daily-plans/[id]/supplement-intakes/[intakeId]",
      params: {
        id: String(dailyPlanId),
        intakeId: String(intake.id),
        returnTo: pathname,
        ...(calendarizedDayId != null ? { calendarizedDayId: String(calendarizedDayId) } : {}),
        ...(pinned ? { pinned: "1" } : {}),
      },
    });
  };

  const addIntake = () => router.push({
    pathname: "/libraries/daily-plans/[id]/supplement-intakes/add",
    params: {
      id: String(dailyPlanId),
      returnTo: pathname,
      ...(calendarizedDayId != null ? { calendarizedDayId: String(calendarizedDayId) } : {}),
      ...(pinned ? { pinned: "1" } : {}),
    },
  });

  return <><View style={styles.list}>
    <PanelSurface>
      {rows.length ? <ComparisonPanelGestureRows
        actions={(intake) => [
          ...(dailyPlanId > 0 ? [{ backgroundColor: "#515151", icon: <Pencil color={tokens.color.entityIconForeground} size={18} />, label: `Editar ${intake.label}`, onPress: () => openDetail(intake) }] : []),
          ...(canMutateOrder ? [{ backgroundColor: tokens.color.danger, icon: <Trash2 color={tokens.color.entityIconForeground} size={18} />, label: `Eliminar ${intake.label}`, onPress: () => remove(intake) }] : []),
        ]}
        canDrag={() => canMutateOrder && savingKey == null}
        itemLabel={(intake) => intake.label}
        items={rows}
        leftActions={(intake) => [
          ...(completionEndpoint ? [{ backgroundColor: tokens.color.supplement, icon: <Check color={tokens.color.entityIconForeground} size={19} strokeWidth={3} />, label: `${intake.status === "completed" ? "Desmarcar" : "Marcar"} ${intake.label} como cumplida`, onPress: () => void toggle(intake) }] : []),
          ...(editable || calendarizedDayId != null ? [{ backgroundColor: "#3A86FF", icon: <Clock color={tokens.color.entityIconForeground} size={19} />, label: `Cambiar hora de ${intake.label}`, onPress: () => setTimeChangeIntake(intake) }] : []),
        ]}
        onReorder={reorder}
        renderRow={(intake, index) => {
        const itemSummary = intake.items.map((item) => `${String(item.supplement.name ?? "Suplemento")} (${doseLabel(item.quantity, item.unit)})`).join(", ");
        return <View style={[styles.intake, index === rows.length - 1 && styles.intakeLast]}>
          <View style={styles.rowContent}>
            <Pressable disabled={dailyPlanId <= 0} onPress={() => runGuardedNavigation(() => openDetail(intake))} style={({ pressed }) => [styles.rowLink, pressed && styles.pressed]}>
              <View style={styles.copy}>
                <View style={styles.titleRow}>
                  <View style={styles.identity}>
                    <EntityIcon entity="supplement" icon={PillBottle} size="compact" />
                    <Text numberOfLines={2} style={styles.title}>{intake.label}</Text>
                  </View>
                  {intake.hour ? <View style={styles.timeGroup}><Clock color={tokens.color.textMuted} size={11} strokeWidth={2} /><Text style={styles.time}>{intake.hour}</Text></View> : null}
                </View>
                <Text style={styles.items}>{itemSummary}</Text>
              </View>
              {dailyPlanId > 0 ? <View style={styles.openAction}><ChevronRight color={tokens.color.textMuted} size={19} strokeWidth={2.2} /></View> : null}
            </Pressable>
          </View>
        </View>;
      }} /> : null}
      {!rows.length ? <PanelEmptyState label="Esta minuta aún no tiene ingestas de suplementos." /> : null}
    </PanelSurface>
    {canAdd && dailyPlanId > 0 ? <View><Button label="+ Agregar ingesta" onPress={addIntake} variant="chipPrimary" /></View> : null}
    {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
  </View>
  <CalendarizedEntityActions
    entityName={timeChangeIntake?.label ?? "Ingesta"}
    initialAction="change-time"
    key={timeChangeIntake?.key ?? "closed-supplement-time-change"}
    onVisibleChange={(visible) => { if (!visible) setTimeChangeIntake(null); }}
    timeChange={timeChangeIntake ? { entity: "supplement", initialTime: timeChangeIntake.hour, onSubmit: (hour) => changeTime(timeChangeIntake, hour) } : undefined}
    visible={timeChangeIntake != null}
  /></>;
}

const styles = StyleSheet.create({
  copy: { flex: 1, gap: tokens.spacing.md, minWidth: 0 },
  identity: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0, paddingHorizontal: tokens.spacing.xs },
  intake: { borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, paddingBottom: tokens.spacing.xl, paddingHorizontal: tokens.spacing.sm, paddingTop: tokens.spacing.xl },
  intakeLast: { borderBottomWidth: 0 },
  items: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: tokens.weight.regular, lineHeight: 21, paddingHorizontal: tokens.spacing.xs },
  list: { gap: tokens.spacing.md },
  openAction: { alignItems: "center", alignSelf: "stretch", borderRadius: tokens.radius.pill, justifyContent: "center", minWidth: 24 },
  pressed: { opacity: 0.68 },
  rowContent: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm },
  rowLink: { alignItems: "center", flex: 1, flexDirection: "row", gap: tokens.spacing.xs, minWidth: 0 },
  time: { color: tokens.color.textMuted, fontSize: tokens.type.label, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.regular },
  timeGroup: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.pill, borderWidth: 1, flexDirection: "row", flexShrink: 0, gap: 4, marginTop: -2, minHeight: 23, paddingHorizontal: tokens.spacing.sm, paddingVertical: 2 },
  title: { color: tokens.color.textMain, flexShrink: 1, fontSize: tokens.type.caption + 1, fontWeight: tokens.weight.semibold, lineHeight: 19, minWidth: 0 },
  titleRow: { alignItems: "flex-start", flexDirection: "row", gap: tokens.spacing.compact, minWidth: 0 },
});
