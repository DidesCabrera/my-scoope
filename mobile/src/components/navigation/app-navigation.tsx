import type { PropsWithChildren } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { type Href, usePathname, useRouter } from "expo-router";
import {
  CalendarClock,
  Camera,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Clock3,
  FileCheck,
  Files,
  BookOpen,
  House,
  PanelRight,
  Pin,
  MoreHorizontal,
  Plus,
  Bell,
  Scale,
  Sparkles,
  TrendingUp,
  UserRound,
  UserPlus,
  WandSparkles,
  WalletCards,
  Weight,
} from "lucide-react-native";
import type { LucideIcon } from "lucide-react-native";
import {
  Animated,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import { initialWindowMetrics, SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Defs, LinearGradient, Rect, Stop } from "react-native-svg";

import { useSession } from "@/auth/session-context";
import type { EntitlementsData, HomeData, LibraryEntity } from "@/api/types";
import { tokens } from "@/design/tokens";
import { listAvailableProductAreas, type ProductAreaKey } from "@/navigation/product-areas";
import { MyScoopeLogo } from "@/components/ui/my-scoope-logo";
import { ModalBackdrop } from "@/components/ui/action-sheet-modal";
import { HeaderEntityIdentity } from "./header-entity-identity";
import { EntitySidebarItem, type EntitySidebarItemData, NavigationSidebarItem, type NavigationSidebarItemData } from "./sidebar-items";

type HeaderAction = { disabled?: boolean; icon?: "back" | "calendar-clock" | "clock" | "more" | "none" | "pin" | "plus"; label: string; onPress(): void };

type HeaderPresentation =
  | { mode: "default"; action?: HeaderAction; createAction?: HeaderAction; identityVisible?: boolean; title?: string }
  | { mode: "back"; action?: HeaderAction; fallback?: Href; forceFallback?: boolean; identityVisible?: boolean; leadingAction?: HeaderAction; title: string }
  | { mode: "library-detail"; action?: HeaderAction; entity: LibraryEntity; identityVisible: boolean; secondaryAction?: HeaderAction; title: string }
  | { mode: "library-list"; action?: HeaderAction; createAction?: { label: string; onPress(): void }; entity: LibraryEntity; identityVisible: boolean; title: string };

type NavigationContextValue = {
  closeMenu(): void;
  finishClosingMenu(): void;
  headerPresentation: HeaderPresentation;
  menuMounted: boolean;
  menuOpen: boolean;
  openMenu(): void;
  setHeaderPresentation(presentation: HeaderPresentation): void;
};

const NavigationContext = createContext<NavigationContextValue | null>(null);

const productAreaIcons: Record<ProductAreaKey, LucideIcon> = {
  assistant: Sparkles,
  comparator: Scale,
  home: House,
  inbox: UserPlus,
  program: CalendarClock,
};

const primaryItems: NavigationSidebarItemData[] = listAvailableProductAreas().map((area) => ({
  href: area.href,
  icon: productAreaIcons[area.key],
  iconTreatment: area.key === "assistant" ? "assistant" : "plain",
  label: area.label,
}));

const secondaryPrimaryItems: NavigationSidebarItemData[] = [
  { href: "/personal-records", icon: Files, label: "Fichas personales" },
  { href: "/system-foundations", icon: BookOpen, label: "Fundamentos Sistema" },
];

const libraryItems: EntitySidebarItemData[] = [
  { entity: "program", href: "/libraries/programs", label: "Mis Programas Semanales" },
  { entity: "dailyPlan", href: "/libraries/daily-plans", label: "Mis Planes Diarios" },
  { entity: "meal", href: "/libraries/meals", label: "Mis Comidas" },
  { entity: "food", href: "/libraries/foods", label: "Mis Alimentos" },
];

function useAppNavigation(): NavigationContextValue {
  const context = useContext(NavigationContext);
  if (!context) throw new Error("useAppNavigation must be used inside AppNavigationProvider");
  return context;
}

export function AppNavigationProvider({ children }: PropsWithChildren) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuMounted, setMenuMounted] = useState(false);
  const [headerPresentation, setHeaderPresentation] = useState<HeaderPresentation>({ mode: "default" });
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  const finishClosingMenu = useCallback(() => setMenuMounted(false), []);
  const openMenu = useCallback(() => { setMenuMounted(true); setMenuOpen(true); }, []);
  const value = useMemo<NavigationContextValue>(() => ({ closeMenu, finishClosingMenu, headerPresentation, menuMounted, menuOpen, openMenu, setHeaderPresentation }), [closeMenu, finishClosingMenu, headerPresentation, menuMounted, menuOpen, openMenu]);
  return (
    <NavigationContext.Provider value={value}>
      {children}
      <AppSidebar />
    </NavigationContext.Provider>
  );
}

function HeaderIdentity({ icon: Icon, title, visible }: { icon: LucideIcon; title: string; visible: boolean }) {
  const [progress] = useState(() => new Animated.Value(visible ? 1 : 0));
  useEffect(() => {
    Animated.timing(progress, { duration: 90, toValue: visible ? 1 : 0, useNativeDriver: true }).start();
  }, [progress, visible]);
  return <Animated.View accessibilityElementsHidden={!visible} importantForAccessibility={visible ? "auto" : "no-hide-descendants"} pointerEvents="none" style={[styles.headerListIdentity, { opacity: progress, transform: [{ translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [-4, 0] }) }] }]}><View accessibilityLabel={title} accessible style={styles.routeIdentity}><Icon color={tokens.color.textMain} size={18} strokeWidth={2.2} /><Text numberOfLines={1} style={styles.routeIdentityTitle}>{title}</Text></View></Animated.View>;
}

function LibraryHeaderIdentity({ entity, title, visible }: { entity: LibraryEntity; title: string; visible: boolean }) {
  const [progress] = useState(() => new Animated.Value(visible ? 1 : 0));
  useEffect(() => { Animated.timing(progress, { duration: 90, toValue: visible ? 1 : 0, useNativeDriver: true }).start(); }, [progress, visible]);
  return <Animated.View accessibilityElementsHidden={!visible} importantForAccessibility={visible ? "auto" : "no-hide-descendants"} pointerEvents="none" style={[styles.headerListIdentity, { opacity: progress }]}><HeaderEntityIdentity entity={entity} title={title} /></Animated.View>;
}

function BackHeaderIdentity({ title, visible = true }: { title: string; visible?: boolean }) {
  const [progress] = useState(() => new Animated.Value(visible ? 1 : 0));
  useEffect(() => { Animated.timing(progress, { duration: 90, toValue: visible ? 1 : 0, useNativeDriver: true }).start(); }, [progress, visible]);
  return <Animated.View accessibilityElementsHidden={!visible} accessibilityLabel={title} accessible importantForAccessibility={visible ? "auto" : "no-hide-descendants"} pointerEvents="none" style={[styles.backHeaderIdentity, { opacity: progress, transform: [{ translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [-4, 0] }) }] }]}><Text numberOfLines={1} style={styles.routeIdentityTitle}>{title}</Text></Animated.View>;
}

function routeHeader(pathname: string): { icon: LucideIcon; title: string } {
  if (pathname.startsWith("/assistant")) return { icon: Sparkles, title: pathname === "/assistant" ? "Asistente Nutricional" : "Conversación" };
  if (pathname.startsWith("/proposals")) return { icon: pathname === "/proposals" ? Sparkles : ClipboardCheck, title: pathname === "/proposals" ? "Asistente Nutricional" : "Detalle de propuesta" };
  if (pathname.startsWith("/comparator")) return { icon: Scale, title: pathname.includes("/saved") ? "Comparaciones guardadas" : "Comparaciones" };
  if (pathname.startsWith("/program")) return { icon: CalendarClock, title: pathname === "/program" ? "Mi programa activo" : pathname.includes("/activate") ? "Calendarizar programa" : "Detalle del día" };
  if (pathname === "/today" || pathname === "/") return { icon: House, title: "Inicio" };
  if (pathname === "/weight") return { icon: Weight, title: "Registrar peso" };
  if (pathname === "/label-capture") return { icon: Camera, title: "Digitalizar etiqueta" };
  if (pathname === "/review") return { icon: TrendingUp, title: "Revisión de progreso" };
  if (pathname === "/revision") return { icon: ClipboardCheck, title: "Revisar ajuste" };
  if (pathname === "/reminders") return { icon: Bell, title: "Recordatorios" };
  if (pathname === "/inbox") return { icon: UserPlus, title: "Compartidos" };
  if (pathname.startsWith("/share/")) return { icon: UserPlus, title: "Plan compartido" };
  if (pathname === "/subscription" || pathname === "/subscription-details") return { icon: WalletCards, title: pathname === "/subscription" ? "Suscripciones y Bolsas" : "Detalles de suscripciones y bolsas" };
  if (pathname === "/account") return { icon: UserRound, title: "Mi cuenta" };
  if (pathname === "/onboarding") return { icon: UserRound, title: "Tu ficha" };
  if (pathname === "/onboarding-preview") return { icon: WandSparkles, title: "Vista previa del onboarding" };
  if (pathname === "/disclosures") return { icon: FileCheck, title: "Información importante" };
  return { icon: UserRound, title: "Cuenta" };
}

export function AppNavigationHeader() {
  const { headerPresentation, openMenu } = useAppNavigation();
  const router = useRouter();
  const pathname = usePathname();
  const { status, profile } = useSession();
  const canOpenMenu = status === "authenticated" && Boolean(profile?.onboarding_completed) && !profile?.review_disclosure_required;
  const detailFallback = headerPresentation.mode === "back"
    ? headerPresentation.fallback ?? "/today"
    : headerPresentation.mode === "library-detail"
    ? headerPresentation.entity === "dailyPlan"
      ? "/libraries/daily-plans"
      : headerPresentation.entity === "program"
        ? "/libraries/programs"
        : headerPresentation.entity === "meal"
          ? "/libraries/meals"
          : "/libraries/foods"
    : "/today";
  const routeIdentity = routeHeader(pathname);
  const isHome = pathname === "/today" || pathname === "/";
  const defaultIdentityVisible = headerPresentation.mode === "default" && Boolean(headerPresentation.identityVisible);
  return (
    <SafeAreaView edges={["top", "left", "right"]} style={styles.headerSafeArea}>
      <View style={styles.header}>
        {headerPresentation.mode === "back" && headerPresentation.leadingAction?.icon === "none" ? (
          <View style={styles.backHeaderLeadingAction} />
        ) : headerPresentation.mode === "back" && headerPresentation.leadingAction ? (
          <Pressable
            accessibilityLabel={headerPresentation.leadingAction.label}
            accessibilityRole="button"
            disabled={headerPresentation.leadingAction.disabled}
            hitSlop={8}
            onPress={headerPresentation.leadingAction.onPress}
            style={({ pressed }) => [styles.backHeaderLeadingAction, headerPresentation.leadingAction?.disabled && styles.disabled, pressed && styles.pressed]}>
            {headerPresentation.leadingAction.icon === "back"
              ? <ChevronLeft color={tokens.color.textMuted} size={26} strokeWidth={2.2} />
              : <Text numberOfLines={1} style={styles.backHeaderActionText}>{headerPresentation.leadingAction.label}</Text>}
          </Pressable>
        ) : headerPresentation.mode === "library-detail" || headerPresentation.mode === "back" ? (
          <Pressable accessibilityLabel="Volver" accessibilityRole="button" hitSlop={8} onPress={() => { if (headerPresentation.mode === "back" && headerPresentation.forceFallback) router.replace(detailFallback); else if (router.canGoBack()) router.back(); else router.replace(detailFallback); }} style={({ pressed }) => [styles.headerButton, headerPresentation.mode === "back" && styles.backHeaderSide, pressed && styles.pressed]}><ChevronLeft color={tokens.color.textMuted} size={26} strokeWidth={2.2} /></Pressable>
        ) : canOpenMenu ? (
          <Pressable
            accessibilityLabel="Abrir menú"
            accessibilityRole="button"
            hitSlop={8}
            onPress={openMenu}
            style={({ pressed }) => [styles.headerButton, pressed && styles.pressed]}>
            <PanelRight color={tokens.color.textMuted} size={25} strokeWidth={2} />
          </Pressable>
        ) : (
          <View style={styles.headerButton} />
        )}
        {headerPresentation.mode === "back" ? <BackHeaderIdentity title={headerPresentation.title} visible={headerPresentation.identityVisible} /> : headerPresentation.mode === "library-list" || headerPresentation.mode === "library-detail" ? (
          <LibraryHeaderIdentity entity={headerPresentation.entity} title={headerPresentation.title} visible={headerPresentation.identityVisible} />
        ) : isHome ? <View pointerEvents="none" style={styles.headerLogo}><MyScoopeLogo /></View> : <HeaderIdentity icon={routeIdentity.icon} title={headerPresentation.title || routeIdentity.title} visible={defaultIdentityVisible} />}
        {headerPresentation.mode === "back" && headerPresentation.action ? (
          <Pressable
            accessibilityLabel={headerPresentation.action.label}
            accessibilityRole="button"
            disabled={headerPresentation.action.disabled}
            hitSlop={8}
            onPress={headerPresentation.action.onPress}
            style={({ pressed }) => [styles.backHeaderAction, headerPresentation.action?.icon === "more" && styles.backHeaderMenuAction, headerPresentation.action?.disabled && styles.disabled, pressed && styles.pressed]}>
            {headerPresentation.action.icon === "more"
              ? <MoreHorizontal color={tokens.color.textMuted} size={26} strokeWidth={2.2} />
              : <Text numberOfLines={1} style={styles.backHeaderActionText}>{headerPresentation.action.label}</Text>}
          </Pressable>
        ) : headerPresentation.mode === "library-list" ? (
          <View style={styles.libraryHeaderActions}>
            {headerPresentation.createAction ? (
              <Pressable
                accessibilityLabel={headerPresentation.createAction.label}
                accessibilityRole="button"
                hitSlop={8}
                onPress={headerPresentation.createAction.onPress}
                style={({ pressed }) => [styles.headerButton, styles.libraryHeaderButton, pressed && styles.pressed]}>
                <Plus color={tokens.color.textMuted} size={25} strokeWidth={2.2} />
              </Pressable>
            ) : null}
            {headerPresentation.action ? (
              <Pressable
                accessibilityLabel={headerPresentation.action.label}
                accessibilityRole="button"
                accessibilityState={{ disabled: headerPresentation.action.disabled }}
                disabled={headerPresentation.action.disabled}
                hitSlop={8}
                onPress={headerPresentation.action.onPress}
                style={({ pressed }) => [headerPresentation.action?.icon === "more" ? [styles.headerButton, styles.libraryHeaderButton] : styles.libraryHeaderTextAction, headerPresentation.action?.disabled && styles.disabled, pressed && styles.pressed]}>
                {headerPresentation.action.icon === "more"
                  ? <MoreHorizontal color={tokens.color.textMuted} size={26} strokeWidth={2.2} />
                  : <Text numberOfLines={1} style={styles.backHeaderActionText}>{headerPresentation.action.label}</Text>}
              </Pressable>
            ) : null}
          </View>
        ) : headerPresentation.mode === "library-detail" && (headerPresentation.secondaryAction || headerPresentation.action) ? (
          <View style={styles.libraryHeaderActions}>
            {headerPresentation.secondaryAction ? (
              <Pressable
                accessibilityLabel={headerPresentation.secondaryAction.label}
                accessibilityRole="button"
                hitSlop={8}
                onPress={headerPresentation.secondaryAction.onPress}
                style={({ pressed }) => [styles.headerButton, styles.libraryHeaderButton, pressed && styles.pressed]}>
                {headerPresentation.secondaryAction.icon === "pin"
                  ? <Pin color={tokens.color.textMuted} fill="none" size={24} strokeWidth={2.2} />
                  : headerPresentation.secondaryAction.icon === "calendar-clock"
                    ? <CalendarClock color={tokens.color.textMuted} size={24} strokeWidth={2.2} />
                    : <Clock3 color={tokens.color.textMuted} size={24} strokeWidth={2.2} />}
              </Pressable>
            ) : null}
            {headerPresentation.action ? (
              <Pressable
                accessibilityLabel={headerPresentation.action.label}
                accessibilityRole="button"
                hitSlop={8}
                onPress={headerPresentation.action.onPress}
                style={({ pressed }) => [styles.headerButton, styles.libraryHeaderButton, pressed && styles.pressed]}>
                <MoreHorizontal color={tokens.color.textMuted} size={26} strokeWidth={2.2} />
              </Pressable>
            ) : null}
          </View>
        ) : headerPresentation.mode === "default" && (headerPresentation.createAction || headerPresentation.action) ? (
          <View style={styles.libraryHeaderActions}>
            {headerPresentation.createAction ? (
              <Pressable
                accessibilityLabel={headerPresentation.createAction.label}
                accessibilityRole="button"
                accessibilityState={{ disabled: headerPresentation.createAction.disabled }}
                disabled={headerPresentation.createAction.disabled}
                hitSlop={8}
                onPress={headerPresentation.createAction.onPress}
                style={({ pressed }) => [styles.headerButton, styles.libraryHeaderButton, headerPresentation.createAction?.disabled && styles.disabled, pressed && styles.pressed]}>
                <Plus color={tokens.color.textMuted} size={25} strokeWidth={2.2} />
              </Pressable>
            ) : null}
            {headerPresentation.action ? (
              <Pressable
                accessibilityLabel={headerPresentation.action.label}
                accessibilityRole="button"
                accessibilityState={{ disabled: headerPresentation.action.disabled }}
                disabled={headerPresentation.action.disabled}
                hitSlop={8}
                onPress={headerPresentation.action.onPress}
                style={({ pressed }) => [styles.headerButton, styles.libraryHeaderButton, headerPresentation.action?.disabled && styles.disabled, pressed && styles.pressed]}>
                {headerPresentation.action.icon === "plus"
                  ? <Plus color={tokens.color.textMuted} size={25} strokeWidth={2.2} />
                  : <MoreHorizontal color={tokens.color.textMuted} size={26} strokeWidth={2.2} />}
              </Pressable>
            ) : null}
          </View>
        ) : <View style={[styles.headerButton, headerPresentation.mode === "back" && styles.backHeaderSide]} />}
      </View>
    </SafeAreaView>
  );
}

export function useHeaderPresentation() {
  return useAppNavigation().setHeaderPresentation;
}

function useSidebarItem(item: { href: Href }) {
  const pathname = usePathname();
  const router = useRouter();
  const { closeMenu } = useAppNavigation();
  const assistantAliasActive = item.href === "/assistant" && pathname.startsWith("/proposals");
  const active = assistantAliasActive || pathname === item.href || (pathname.startsWith(String(item.href)) && item.href !== "/today");
  return { active, onPress: () => { closeMenu(); router.push(item.href); } };
}

function FunctionalSidebarEntry({ item }: { item: NavigationSidebarItemData }) {
  const state = useSidebarItem(item);
  return <NavigationSidebarItem {...state} icon={item.icon} iconTreatment={item.iconTreatment} label={item.label} />;
}

function EntitySidebarEntry({ count, item }: { count: number | null; item: EntitySidebarItemData }) {
  const state = useSidebarItem(item);
  return <EntitySidebarItem {...state} count={count} entity={item.entity} label={item.label} />;
}

function libraryCount(counts: HomeData["library_counts"] | null, entity: LibraryEntity): number | null {
  if (!counts) return null;
  return entity === "dailyPlan" ? counts.daily_plan : counts[entity];
}

function AppSidebar() {
  const { width } = useWindowDimensions();
  const drawerWidth = Math.min(width * 0.88, 360);
  const insets = useSafeAreaInsets();
  const { closeMenu, finishClosingMenu, menuMounted, menuOpen } = useAppNavigation();
  const { apiRequest, session, status } = useSession();
  const router = useRouter();
  const [creditSummary, setCreditSummary] = useState<{ availableCredits: number; planName: string } | null>(null);
  const [libraryCounts, setLibraryCounts] = useState<HomeData["library_counts"] | null>(null);
  const [translateX] = useState(() => new Animated.Value(-380));
  const [scrimOpacity] = useState(() => new Animated.Value(0));

  useEffect(() => {
    const hiddenPosition = -drawerWidth;
    if (menuOpen) {
      translateX.setValue(hiddenPosition);
      scrimOpacity.setValue(0);
      Animated.parallel([
        Animated.timing(translateX, { duration: 220, toValue: 0, useNativeDriver: true }),
        Animated.timing(scrimOpacity, { duration: 220, toValue: 1, useNativeDriver: true }),
      ]).start();
      return;
    }
    if (!menuMounted) return;
    Animated.parallel([
      Animated.timing(translateX, { duration: 220, toValue: hiddenPosition, useNativeDriver: true }),
      Animated.timing(scrimOpacity, { duration: 180, toValue: 0, useNativeDriver: true }),
    ]).start(({ finished }) => { if (finished) finishClosingMenu(); });
  }, [drawerWidth, finishClosingMenu, menuMounted, menuOpen, scrimOpacity, translateX]);

  useEffect(() => {
    if (!menuOpen || status !== "authenticated") return;
    void apiRequest<EntitlementsData>("/api/v1/entitlements")
      .then((entitlements) => setCreditSummary({ availableCredits: entitlements.available_credits, planName: entitlements.plan_name }))
      .catch(() => undefined);
    void apiRequest<HomeData>("/api/v1/home")
      .then((home) => setLibraryCounts(home.library_counts))
      .catch(() => undefined);
  }, [apiRequest, menuOpen, status]);

  const openCredits = () => {
    closeMenu();
    router.push("/subscription" as Href);
  };
  const openHome = () => {
    closeMenu();
    router.push("/today" as Href);
  };

  return (
    <Modal animationType="none" onRequestClose={closeMenu} transparent visible={menuMounted}>
      <View style={styles.modalRoot}>
        <Animated.View style={[styles.scrim, { opacity: scrimOpacity }]}><ModalBackdrop accessibilityLabel="Cerrar menú" onPress={closeMenu} /></Animated.View>
        <Animated.View style={[styles.drawer, { maxWidth: 360, transform: [{ translateX }], width: drawerWidth }]}>
          <View style={[styles.drawerSafeArea, {
            paddingBottom: Math.max(insets.bottom, initialWindowMetrics?.insets.bottom ?? 0),
            paddingLeft: Math.max(insets.left, initialWindowMetrics?.insets.left ?? 0),
            paddingTop: Math.max(insets.top, initialWindowMetrics?.insets.top ?? 0),
          }]}>
            <View style={styles.drawerHeader}>
              <Pressable accessibilityLabel="Ir a Inicio" accessibilityRole="button" hitSlop={8} onPress={openHome} style={({ pressed }) => [styles.drawerHome, pressed && styles.pressed]}>
                <MyScoopeLogo />
              </Pressable>
              <Pressable
                accessibilityLabel="Cerrar menú"
                accessibilityRole="button"
                onPress={closeMenu}
                style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}>
                <PanelRight color={tokens.color.textMuted} size={24} strokeWidth={2} />
              </Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.drawerContent} showsVerticalScrollIndicator={false} style={styles.drawerScroll}>
              {primaryItems.flatMap((item) => [
                <FunctionalSidebarEntry item={item} key={String(item.href)} />,
                ...(item.href === "/inbox"
                  ? secondaryPrimaryItems.map((secondaryItem) => <FunctionalSidebarEntry item={secondaryItem} key={String(secondaryItem.href)} />)
                  : []),
              ])}
              <View style={styles.menuSection}>
                <Text style={styles.menuSectionLabel}>Mis librerías</Text>
                {libraryItems.map((item) => <EntitySidebarEntry count={libraryCount(libraryCounts, item.entity)} item={item} key={String(item.href)} />)}
              </View>
              <View style={styles.menuSection}>
                <Text style={styles.menuSectionLabel}>Cuenta</Text>
                <FunctionalSidebarEntry item={{ href: "/account", icon: UserRound, label: "Mi cuenta" }} />
                {session?.is_staff ? <FunctionalSidebarEntry item={{ href: "/onboarding-preview", icon: WandSparkles, label: "Vista previa del onboarding" }} /> : null}
              </View>
            </ScrollView>
            {creditSummary ? (
              <View style={[styles.creditDashboardShadow, { width: drawerWidth - tokens.spacing.md }]}>
                <Pressable accessibilityLabel="Abrir Suscripciones y bolsas" accessibilityRole="button" onPress={openCredits} style={({ pressed }) => [styles.creditDashboard, pressed && styles.creditDashboardPressed]}>
                  <Svg aria-hidden height="100%" pointerEvents="none" style={StyleSheet.absoluteFill} width="100%">
                    <Defs>
                      <LinearGradient id="sidebar-credit-macros" x1="0" x2="1" y1="0" y2="1">
                        <Stop offset="0" stopColor={tokens.color.protein} />
                        <Stop offset="0.5" stopColor={tokens.color.carbs} />
                        <Stop offset="1" stopColor={tokens.color.fat} />
                      </LinearGradient>
                    </Defs>
                    <Rect fill="url(#sidebar-credit-macros)" height="100%" rx={tokens.radius.panel} ry={tokens.radius.panel} width="100%" />
                  </Svg>
                  <View style={styles.creditDashboardPlan}>
                    <Text style={styles.creditDashboardEyebrow}>Plan</Text>
                    <Text numberOfLines={1} style={styles.creditDashboardPlanTitle}>{creditSummary.planName}</Text>
                  </View>
                  <View style={styles.creditDashboardCredits}>
                    <Text style={styles.creditDashboardCreditValue}>{creditSummary.availableCredits}</Text>
                    <Text numberOfLines={1} style={styles.creditDashboardAvailableLabel}>créditos disponibles</Text>
                  </View>
                  <View style={styles.creditDashboardAction}>
                    <ChevronRight color={tokens.color.surfaceApp} size={21} strokeWidth={2.4} />
                  </View>
                </Pressable>
              </View>
            ) : null}
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.65 },
  disabled: { opacity: 0.35 },
  headerSafeArea: { backgroundColor: tokens.color.surfaceApp },
  header: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, flexDirection: "row", height: 48, justifyContent: "space-between" },
  headerButton: { alignItems: "center", height: 52, justifyContent: "center", width: 58 },
  libraryHeaderButton: { width: 44 },
  libraryHeaderTextAction: { alignItems: "center", height: 52, justifyContent: "center", paddingHorizontal: tokens.spacing.lg },
  libraryHeaderActions: { alignItems: "center", flexDirection: "row" },
  backHeaderSide: { alignItems: "flex-start", paddingLeft: tokens.spacing.lg, width: 92 },
  backHeaderLeadingAction: { alignItems: "flex-start", height: 52, justifyContent: "center", paddingLeft: tokens.spacing.lg, width: 92 },
  backHeaderAction: { alignItems: "center", height: 52, justifyContent: "center", paddingHorizontal: tokens.spacing.sm, width: 92 },
  backHeaderMenuAction: { alignItems: "flex-end", paddingHorizontal: 0, paddingRight: tokens.spacing.sm, width: 92 },
  backHeaderActionText: { color: tokens.color.textMain, fontSize: tokens.type.caption, fontWeight: "700" },
  backHeaderIdentity: { alignItems: "center", flex: 1, justifyContent: "center", minWidth: 0 },
  headerListIdentity: { flex: 1, justifyContent: "center" },
  headerLogo: { alignItems: "center", bottom: 0, justifyContent: "center", left: 58, position: "absolute", right: 58, top: 0 },
  routeIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  routeIdentityTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, fontWeight: "600", lineHeight: 22 },
  modalRoot: { flex: 1, flexDirection: "row" },
  scrim: { bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  drawer: { backgroundColor: tokens.color.surfaceApp, height: "100%", shadowColor: "#000000", shadowOffset: { height: 0, width: 8 }, shadowOpacity: 0.45, shadowRadius: 20 },
  drawerSafeArea: { flex: 1 },
  drawerHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", minHeight: 64, paddingHorizontal: tokens.spacing.md * 2 },
  drawerHome: { alignItems: "center", justifyContent: "center", minHeight: 44 },
  closeButton: { alignItems: "center", borderRadius: tokens.radius.md, height: 44, justifyContent: "center", width: 44 },
  drawerContent: { gap: 0, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.lg },
  drawerScroll: { flex: 1 },
  creditDashboardShadow: { alignSelf: "flex-start", borderRadius: tokens.radius.panel, elevation: 5, marginBottom: tokens.spacing.md, marginHorizontal: tokens.spacing.md, shadowColor: "#000000", shadowOffset: { height: 5, width: 0 }, shadowOpacity: 0.24, shadowRadius: 9 },
  creditDashboard: { alignItems: "center", borderRadius: tokens.radius.panel, flexDirection: "row", gap: tokens.spacing.compact, minHeight: 58, overflow: "hidden", paddingLeft: tokens.spacing.md },
  creditDashboardPressed: { opacity: 0.72 },
  creditDashboardPlan: { flex: 1, gap: 0, minWidth: 0, paddingLeft: tokens.spacing.xs },
  creditDashboardCredits: { alignItems: "flex-end", flexShrink: 1, gap: 0, minWidth: 0 },
  creditDashboardEyebrow: { color: tokens.color.surfaceApp, fontSize: 9, fontWeight: tokens.weight.bold, letterSpacing: 0.8, lineHeight: 9, opacity: 0.72, textTransform: "uppercase" },
  creditDashboardPlanTitle: { color: tokens.color.surfaceApp, fontSize: 24, fontWeight: tokens.weight.bold, lineHeight: 26 },
  creditDashboardCreditValue: { color: tokens.color.surfaceApp, fontSize: 15, fontVariant: ["tabular-nums"], fontWeight: tokens.weight.bold, lineHeight: 17 },
  creditDashboardAvailableLabel: { color: tokens.color.surfaceApp, flexShrink: 1, fontSize: 10, fontWeight: tokens.weight.medium, lineHeight: 11 },
  creditDashboardAction: { alignItems: "center", borderRadius: tokens.radius.sm, height: 30, justifyContent: "center", marginRight: tokens.spacing.md, width: 30 },
  menuSection: { gap: 0, marginTop: tokens.spacing.md, paddingTop: tokens.spacing.lg },
  menuSectionLabel: { color: tokens.color.textSoft, fontSize: tokens.type.caption, fontWeight: tokens.component.eyebrow.fontWeight, letterSpacing: 1.1, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm, textTransform: "uppercase" },
});
