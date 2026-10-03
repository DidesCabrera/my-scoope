import { type Href, Redirect, useFocusEffect, useRouter } from "expo-router";
import * as Linking from "expo-linking";
import { CircleDollarSign, ExternalLink, FileText, Flag, LifeBuoy, Pencil, Trash2, X } from "lucide-react-native";
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useCallback, useState } from "react";
import { SafeAreaView } from "react-native-safe-area-context";

import { userFacingError } from "@/api/errors";
import type { AccountDeletionData, EntitlementsData, SessionData } from "@/api/types";
import { useSession } from "@/auth/session-context";
import { AssistantCreditBalance } from "@/components/assistant/assistant-credit-balance";
import { useHeaderPresentation } from "@/components/navigation/app-navigation";
import { ProposalReviewSection } from "@/components/proposals/proposal-detail";
import { AppHeader, Button, Card, Field, InlineNotice, Screen, textStyles } from "@/components/ui";
import { ActionSheetModal } from "@/components/ui/action-sheet-modal";
import { appConfig } from "@/config/app-config";
import { tokens } from "@/design/tokens";
import { subscriptionPlanAccent } from "@/presentation/subscription";

const supportEmail = "felipe@myscoope.com";

function joinedDateLabel(value?: string): string {
  if (!value) return "No disponible";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "No disponible";
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric" }).format(date);
}

export default function AccountScreen() {
  const router = useRouter();
  const { status, session, apiRequest, refreshSession, signOut } = useSession();
  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entitlements, setEntitlements] = useState<EntitlementsData | null>(null);
  const [subscriptionError, setSubscriptionError] = useState<string | null>(null);
  const [accountActions, setAccountActions] = useState<"menu" | "rename" | "delete" | null>(null);
  const [compactHeaderVisible, setCompactHeaderVisible] = useState(false);
  const setHeaderPresentation = useHeaderPresentation();

  const openAccountActions = useCallback(() => {
    setUsername(session?.username ?? "");
    setAccountActions("menu");
  }, [session?.username]);
  const closeAccountActions = useCallback(() => {
    setAccountActions(null);
    setConfirmation("");
    setPassword("");
    setUsername("");
    setError(null);
  }, []);

  const openExternalAction = useCallback((url: string) => {
    setAccountActions(null);
    void Linking.openURL(url);
  }, []);

  useFocusEffect(useCallback(() => {
    setHeaderPresentation({
      action: { label: "Acciones de mi cuenta", onPress: openAccountActions },
      identityVisible: compactHeaderVisible,
      mode: "default",
      title: "Mi cuenta",
    });
    return () => setHeaderPresentation({ mode: "default" });
  }, [compactHeaderVisible, openAccountActions, setHeaderPresentation]));

  useFocusEffect(useCallback(() => {
    if (status !== "authenticated") return;
    setSubscriptionError(null);
    void apiRequest<EntitlementsData>("/api/v1/entitlements")
      .then(setEntitlements)
      .catch((nextError) => setSubscriptionError(userFacingError(nextError)));
  }, [apiRequest, status]));

  if (status === "anonymous") return <Redirect href="/login" />;

  async function deleteAccount() {
    setBusy(true);
    setError(null);
    try {
      const result = await apiRequest<AccountDeletionData>("/api/v1/account/delete", {
        method: "POST",
        body: JSON.stringify({ confirmation, password }),
      });
      await signOut();
      Alert.alert("Cuenta eliminada", `Tu acceso fue revocado. Comprobante: ${result.receipt_id}`);
      router.replace("/login");
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  async function renameUsername() {
    const cleanUsername = username.trim();
    if (!cleanUsername) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest<SessionData>("/api/v1/account/username", {
        method: "PATCH",
        body: JSON.stringify({ username: cleanUsername }),
      });
      await refreshSession();
      setAccountActions(null);
      Alert.alert("Nombre de usuario actualizado", `Ahora tu nombre de usuario es “${cleanUsername}”.`);
    } catch (nextError) {
      setError(userFacingError(nextError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen headerMode="preserve" onHeaderVisibilityChange={setCompactHeaderVisible}>
      <AppHeader eyebrow="Mi cuenta" title={session?.display_name || session?.username || "My Scoope"} />
      <Card accent={subscriptionPlanAccent(entitlements?.plan_name)}>
        <View style={styles.subscriptionHeading}>
          <View style={styles.headerCopy}>
            <Text style={styles.eyebrow}>SUSCRIPCIÓN ACTUAL</Text>
            <Text style={styles.planName}>{entitlements?.plan_name ?? "Consultando…"}</Text>
          </View>
        </View>
        {entitlements ? <AssistantCreditBalance availability={entitlements} contained /> : null}
        {subscriptionError ? <InlineNotice tone="error">{subscriptionError}</InlineNotice> : null}
        <Button label="Mejorar mi suscripción" onPress={() => router.push("/subscription" as Href)} variant="multicolor" />
      </Card>
      <ProposalReviewSection eyebrow="CUENTA" title="Información de la cuenta">
        <AccountInformationRows items={[
          { label: "Nombre de usuario", value: session?.username ?? "—" },
          { label: "Correo electrónico", value: session?.email || "No disponible" },
          { label: "Fecha de ingreso", value: joinedDateLabel(session?.date_joined) },
        ]} />
      </ProposalReviewSection>
      {__DEV__ ? (
        <Button label="Abrir galería del sistema UI" onPress={() => router.push("/dev/ui-gallery" as Href)} variant="secondary" />
      ) : null}
      <Button label="Cerrar sesión" onPress={() => void signOut().then(() => router.replace("/login"))} variant="secondary" />
      <InlineNotice tone="warning">My Scoope no reemplaza atención médica. Revisa cualquier cálculo, lectura OCR o propuesta asistida por IA antes de aplicarla.</InlineNotice>
      <ActionSheetModal onRequestClose={closeAccountActions} visible={accountActions != null}>
        <SafeAreaView edges={["left", "right"]} style={styles.sheetSafeArea}>
          <View style={styles.sheetHeader}>
            <View style={styles.headerCopy}>
              <Text style={styles.eyebrow}>{accountActions === "rename" ? "NOMBRE" : "ACCIONES"}</Text>
              <Text style={styles.sheetTitle}>{accountActions === "delete" ? "Eliminar mi cuenta" : accountActions === "rename" ? "Editar nombre de usuario" : "Mi cuenta"}</Text>
            </View>
            <Pressable accessibilityLabel="Cerrar" accessibilityRole="button" onPress={closeAccountActions} style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}>
              <X color={tokens.color.textMain} size={22} />
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.sheetContent} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
            {accountActions === "menu" ? (
              <View>
                <AccountAction icon={Pencil} label="Editar nombre de usuario" onPress={() => { setUsername(session?.username ?? ""); setError(null); setAccountActions("rename"); }} />
                <AccountAction icon={ExternalLink} label="Política de privacidad" onPress={() => openExternalAction(`${appConfig.apiBaseUrl}/privacy/`)} />
                <AccountAction icon={FileText} label="Términos de uso" onPress={() => openExternalAction(`${appConfig.apiBaseUrl}/terms/`)} />
                <AccountAction icon={CircleDollarSign} label="Cancelaciones y reembolsos" onPress={() => openExternalAction(`${appConfig.apiBaseUrl}/refund-policy/`)} />
                <AccountAction icon={LifeBuoy} label="Centro de soporte" onPress={() => openExternalAction(`${appConfig.apiBaseUrl}/support/`)} />
                <AccountAction icon={Flag} label="Reportar contenido o un problema" onPress={() => openExternalAction(`mailto:${supportEmail}?subject=Reporte%20desde%20My%20Scoope`)} />
                <AccountAction destructive icon={Trash2} label="Eliminar cuenta" onPress={() => setAccountActions("delete")} />
              </View>
            ) : accountActions === "rename" ? (
              <View style={styles.deletionForm}>
                <Field autoCapitalize="none" autoCorrect={false} label="Nombre de usuario" onChangeText={(value) => setUsername(value.slice(0, 150))} value={username} />
                {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
                <Button disabled={!username.trim() || username.trim() === session?.username} label="Guardar nombre" loading={busy} onPress={() => void renameUsername()} />
                <Button disabled={busy} label="Volver" onPress={() => { setError(null); setAccountActions("menu"); }} variant="secondary" />
              </View>
            ) : (
              <View style={styles.deletionForm}>
                <Text style={textStyles.muted}>Esta acción revoca el acceso inmediatamente y elimina o anonimiza tus datos conforme a nuestra política. No se puede deshacer.</Text>
                <Field autoCapitalize="characters" label="Escribe ELIMINAR para confirmar" onChangeText={setConfirmation} value={confirmation} />
                <Field label="Contraseña (si tu cuenta usa una)" onChangeText={setPassword} secureTextEntry value={password} />
                {error ? <InlineNotice tone="error">{error}</InlineNotice> : null}
                <Button disabled={confirmation !== "ELIMINAR"} label="Eliminar cuenta definitivamente" loading={busy} onPress={deleteAccount} variant="danger" />
                <Button label="Volver" onPress={() => setAccountActions("menu")} variant="secondary" />
              </View>
            )}
          </ScrollView>
        </SafeAreaView>
      </ActionSheetModal>
    </Screen>
  );
}

function AccountInformationRows({ items }: { items: { label: string; value: string }[] }) {
  return (
    <View style={styles.informationRows}>
      {items.map((item, index) => (
        <View key={item.label} style={[styles.informationRow, index === items.length - 1 && styles.informationRowLast]}>
          <Text style={styles.informationLabel}>{item.label}</Text>
          <Text adjustsFontSizeToFit minimumFontScale={0.72} numberOfLines={1} selectable style={styles.informationValue}>{item.value}</Text>
        </View>
      ))}
    </View>
  );
}

function AccountAction({ destructive = false, icon: Icon, label, onPress }: { destructive?: boolean; icon: typeof Trash2; label: string; onPress(): void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.actionRow, pressed && styles.pressed]}>
      <View style={styles.actionIcon}><Icon color={destructive ? tokens.color.danger : tokens.color.textMain} size={20} /></View>
      <Text style={[styles.actionLabel, destructive && styles.actionLabelDanger]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  actionIcon: { alignItems: "center", backgroundColor: tokens.color.surfaceMuted, borderRadius: tokens.radius.md, height: 38, justifyContent: "center", width: 38 },
  actionLabel: { color: tokens.color.textMain, flex: 1, fontSize: tokens.type.body, fontWeight: tokens.weight.bold },
  actionLabelDanger: { color: tokens.color.danger },
  actionRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 58, paddingVertical: tokens.spacing.sm },
  closeButton: { alignItems: "center", height: 42, justifyContent: "center", width: 42 },
  deletionForm: { gap: tokens.spacing.md },
  eyebrow: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1 },
  headerCopy: { flex: 1, gap: 3, minWidth: 0 },
  informationLabel: { color: tokens.color.textMuted, flex: 1, fontSize: 14, lineHeight: 20 },
  informationRow: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, minHeight: 46, paddingVertical: tokens.spacing.xs },
  informationRowLast: { borderBottomWidth: 0 },
  informationRows: { marginTop: -tokens.spacing.xs },
  informationValue: { color: tokens.color.textMain, flex: 1, fontSize: 14, fontWeight: tokens.weight.bold, lineHeight: 20, textAlign: "right" },
  pressed: { opacity: 0.65 },
  sheetContent: { gap: tokens.spacing.md, padding: tokens.spacing.screen, paddingBottom: tokens.spacing.xl },
  sheetHeader: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", gap: tokens.spacing.md, justifyContent: "space-between", paddingHorizontal: tokens.spacing.screen, paddingVertical: tokens.spacing.md },
  sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, borderTopLeftRadius: tokens.radius.card, borderTopRightRadius: tokens.radius.card, maxHeight: "88%", overflow: "hidden" },
  sheetTitle: { color: tokens.color.textMain, fontSize: tokens.type.section, fontWeight: tokens.weight.extraBold },
  planName: { color: tokens.color.textMain, fontSize: 26, fontWeight: tokens.weight.extraBold },
  subscriptionHeading: { alignItems: "center", flexDirection: "row" },
});
