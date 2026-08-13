import type { PropsWithChildren } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { type Href, usePathname, useRouter } from "expo-router";
import {
  CalendarDays,
  Camera,
  ChevronLeft,
  ClipboardCheck,
  FileCheck,
  House,
  LogOut,
  Menu,
  Bell,
  Scale,
  Sparkles,
  TrendingUp,
  UserRound,
  WalletCards,
  Weight,
  X,
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
import { SafeAreaView } from "react-native-safe-area-context";

import { useSession } from "@/auth/session-context";
import type { LibraryEntity } from "@/api/types";
import { tokens } from "@/design/tokens";
import { listAvailableProductAreas, type ProductAreaKey } from "@/navigation/product-areas";
import { HeaderEntityIdentity } from "./header-entity-identity";
import { EntitySidebarItem, type EntitySidebarItemData, NavigationSidebarItem, type NavigationSidebarItemData } from "./sidebar-items";

type HeaderPresentation =
  | { mode: "default"; borderVisible?: boolean; identityVisible?: boolean; title?: string }
  | { mode: "library-detail"; entity: LibraryEntity; identityVisible: boolean; title: string }
  | { mode: "library-list"; entity: LibraryEntity; identityVisible: boolean; title: string };

type NavigationContextValue = {
  closeMenu(): void;
  headerPresentation: HeaderPresentation;
  menuOpen: boolean;
  openMenu(): void;
  setHeaderPresentation(presentation: HeaderPresentation): void;
};

const NavigationContext = createContext<NavigationContextValue | null>(null);

const productAreaIcons: Record<ProductAreaKey, LucideIcon> = {
  assistant: Sparkles,
  comparator: Scale,
  home: House,
  program: CalendarDays,
  proposals: ClipboardCheck,
};

const primaryItems: NavigationSidebarItemData[] = listAvailableProductAreas().map((area) => ({
  href: area.href,
  icon: productAreaIcons[area.key],
  label: area.label,
}));

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
  const [headerPresentation, setHeaderPresentation] = useState<HeaderPresentation>({ mode: "default" });
  const closeMenu = useCallback(() => setMenuOpen(false), []);
  const openMenu = useCallback(() => setMenuOpen(true), []);
  const value = useMemo<NavigationContextValue>(() => ({ closeMenu, headerPresentation, menuOpen, openMenu, setHeaderPresentation }), [closeMenu, headerPresentation, menuOpen, openMenu]);
  return (
    <NavigationContext.Provider value={value}>
      {children}
      <AppSidebar />
    </NavigationContext.Provider>
  );
}

function MyScoopeLogo() {
  return (
    <View accessibilityLabel="My Scoope" accessible style={styles.logo}>
      <Text style={styles.logoText}>MyScoope</Text>
      <View aria-hidden style={styles.logoBars}>
        <View style={[styles.logoBar, styles.logoBarProtein]} />
        <View style={[styles.logoBar, styles.logoBarCarbs]} />
        <View style={[styles.logoBar, styles.logoBarFat]} />
      </View>
    </View>
  );
}

function HeaderIdentity({ icon: Icon, title, visible }: { icon: LucideIcon; title: string; visible: boolean }) {
  const [progress] = useState(() => new Animated.Value(visible ? 1 : 0));
  useEffect(() => {
    Animated.timing(progress, { duration: 180, toValue: visible ? 1 : 0, useNativeDriver: true }).start();
  }, [progress, visible]);
  return <Animated.View accessibilityElementsHidden={!visible} importantForAccessibility={visible ? "auto" : "no-hide-descendants"} pointerEvents="none" style={[styles.headerListIdentity, { opacity: progress, transform: [{ translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [-4, 0] }) }] }]}><View accessibilityLabel={title} accessible style={styles.routeIdentity}><Icon color={tokens.color.textMain} size={18} strokeWidth={2.2} /><Text numberOfLines={1} style={styles.routeIdentityTitle}>{title}</Text></View></Animated.View>;
}

function LibraryHeaderIdentity({ entity, title, visible }: { entity: LibraryEntity; title: string; visible: boolean }) {
  const [progress] = useState(() => new Animated.Value(visible ? 1 : 0));
  useEffect(() => { Animated.timing(progress, { duration: 180, toValue: visible ? 1 : 0, useNativeDriver: true }).start(); }, [progress, visible]);
  return <Animated.View accessibilityElementsHidden={!visible} importantForAccessibility={visible ? "auto" : "no-hide-descendants"} pointerEvents="none" style={[styles.headerListIdentity, { opacity: progress }]}><HeaderEntityIdentity entity={entity} title={title} /></Animated.View>;
}

function routeHeader(pathname: string): { icon: LucideIcon; title: string } {
  if (pathname.startsWith("/assistant")) return { icon: Sparkles, title: pathname === "/assistant" ? "Asistente" : "Conversación" };
  if (pathname.startsWith("/proposals")) return { icon: ClipboardCheck, title: pathname === "/proposals" ? "Propuestas" : "Detalle de propuesta" };
  if (pathname.startsWith("/comparator")) return { icon: Scale, title: pathname.includes("/saved") ? "Comparaciones guardadas" : "Comparador" };
  if (pathname.startsWith("/program")) return { icon: CalendarDays, title: pathname === "/program" ? "Mi programa" : pathname.includes("/activate") ? "Calendarizar programa" : "Detalle del día" };
  if (pathname === "/today" || pathname === "/") return { icon: House, title: "Inicio" };
  if (pathname === "/weight") return { icon: Weight, title: "Registrar peso" };
  if (pathname === "/label-capture") return { icon: Camera, title: "Digitalizar etiqueta" };
  if (pathname === "/check-in") return { icon: FileCheck, title: "Check-in del día" };
  if (pathname === "/review") return { icon: TrendingUp, title: "Revisión de progreso" };
  if (pathname === "/revision") return { icon: ClipboardCheck, title: "Revisar ajuste" };
  if (pathname === "/reminders") return { icon: Bell, title: "Recordatorios" };
  if (pathname === "/subscription") return { icon: WalletCards, title: "Mi suscripción" };
  if (pathname === "/account") return { icon: UserRound, title: "Mi cuenta" };
  if (pathname === "/onboarding") return { icon: UserRound, title: "Tu ficha" };
  if (pathname === "/disclosures") return { icon: FileCheck, title: "Información importante" };
  return { icon: UserRound, title: "Cuenta" };
}

export function AppNavigationHeader() {
  const { headerPresentation, openMenu } = useAppNavigation();
  const router = useRouter();
  const pathname = usePathname();
  const { status, profile } = useSession();
  const canOpenMenu = status === "authenticated" && Boolean(profile?.onboarding_completed) && !profile?.review_disclosure_required;
  const detailFallback = headerPresentation.mode === "library-detail"
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
      <View style={[styles.header, headerPresentation.mode === "default" ? !defaultIdentityVisible && styles.headerWithoutBorder : !headerPresentation.identityVisible && styles.headerWithoutBorder]}>
        {headerPresentation.mode === "library-detail" ? (
          <Pressable accessibilityLabel="Volver" accessibilityRole="button" hitSlop={8} onPress={() => { if (router.canGoBack()) router.back(); else router.replace(detailFallback); }} style={({ pressed }) => [styles.headerButton, pressed && styles.pressed]}><ChevronLeft color={tokens.color.textMain} size={26} strokeWidth={2.2} /></Pressable>
        ) : canOpenMenu ? (
          <Pressable
            accessibilityLabel="Abrir menú"
            accessibilityRole="button"
            hitSlop={8}
            onPress={openMenu}
            style={({ pressed }) => [styles.headerButton, pressed && styles.pressed]}>
            <Menu color={tokens.color.textMain} size={25} strokeWidth={2} />
          </Pressable>
        ) : (
          <View style={styles.headerButton} />
        )}
        {headerPresentation.mode === "library-list" || headerPresentation.mode === "library-detail" ? (
          <LibraryHeaderIdentity entity={headerPresentation.entity} title={headerPresentation.title} visible={headerPresentation.identityVisible} />
        ) : isHome ? <View pointerEvents="none" style={styles.headerLogo}><MyScoopeLogo /></View> : <HeaderIdentity icon={routeIdentity.icon} title={headerPresentation.title || routeIdentity.title} visible={defaultIdentityVisible} />}
        <View style={styles.headerButton} />
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
  const active = pathname === item.href || (pathname.startsWith(String(item.href)) && item.href !== "/today");
  return { active, onPress: () => { closeMenu(); router.push(item.href); } };
}

function FunctionalSidebarEntry({ item }: { item: NavigationSidebarItemData }) {
  const state = useSidebarItem(item);
  return <NavigationSidebarItem {...state} icon={item.icon} label={item.label} />;
}

function EntitySidebarEntry({ item }: { item: EntitySidebarItemData }) {
  const state = useSidebarItem(item);
  return <EntitySidebarItem {...state} entity={item.entity} label={item.label} />;
}

function AppSidebar() {
  const { width } = useWindowDimensions();
  const router = useRouter();
  const { closeMenu, menuOpen } = useAppNavigation();
  const { session, signOut } = useSession();
  const [translateX] = useState(() => new Animated.Value(-380));

  useEffect(() => {
    if (!menuOpen) return;
    translateX.setValue(-Math.min(width * 0.88, 360));
    Animated.timing(translateX, {
      duration: 220,
      toValue: 0,
      useNativeDriver: true,
    }).start();
  }, [menuOpen, translateX, width]);

  return (
    <Modal animationType="fade" onRequestClose={closeMenu} transparent visible={menuOpen}>
      <View style={styles.modalRoot}>
        <Pressable accessibilityLabel="Cerrar menú" onPress={closeMenu} style={styles.scrim} />
        <Animated.View style={[styles.drawer, { maxWidth: 360, transform: [{ translateX }], width: Math.min(width * 0.88, 360) }]}>
          <SafeAreaView edges={["top", "bottom", "left"]} style={styles.drawerSafeArea}>
            <View style={styles.drawerHeader}>
              <MyScoopeLogo />
              <Pressable
                accessibilityLabel="Cerrar menú"
                accessibilityRole="button"
                onPress={closeMenu}
                style={({ pressed }) => [styles.closeButton, pressed && styles.pressed]}>
                <X color={tokens.color.textMain} size={24} />
              </Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.drawerContent}>
              {primaryItems.map((item) => <FunctionalSidebarEntry item={item} key={String(item.href)} />)}
              <View style={styles.menuSection}>
                <Text style={styles.menuSectionLabel}>Mis librerías</Text>
                {libraryItems.map((item) => <EntitySidebarEntry item={item} key={String(item.href)} />)}
              </View>
              <View style={styles.menuSection}>
                <Text style={styles.menuSectionLabel}>Cuenta</Text>
                <FunctionalSidebarEntry item={{ href: "/account", icon: UserRound, label: "Mi cuenta" }} />
              </View>
            </ScrollView>
            <View style={styles.drawerFooter}>
              <View style={styles.accountCopy}>
                <Text numberOfLines={1} style={styles.accountName}>{session?.display_name || session?.username || "My Scoope"}</Text>
                <Text numberOfLines={1} style={styles.accountEmail}>{session?.email}</Text>
              </View>
              <Pressable
                accessibilityLabel="Cerrar sesión"
                accessibilityRole="button"
                onPress={() => {
                  closeMenu();
                  void signOut().then(() => router.replace("/login"));
                }}
                style={({ pressed }) => [styles.signOutButton, pressed && styles.pressed]}>
                <LogOut color={tokens.color.textMuted} size={20} />
              </Pressable>
            </View>
          </SafeAreaView>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  pressed: { opacity: 0.65 },
  headerSafeArea: { backgroundColor: tokens.color.surfaceApp },
  header: { alignItems: "center", backgroundColor: tokens.color.surfaceApp, borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", height: 58, justifyContent: "space-between" },
  headerWithoutBorder: { borderBottomWidth: 0 },
  headerButton: { alignItems: "center", height: 52, justifyContent: "center", width: 58 },
  headerListIdentity: { flex: 1, justifyContent: "center" },
  headerLogo: { alignItems: "center", bottom: 0, justifyContent: "center", left: 58, position: "absolute", right: 58, top: 0 },
  routeIdentity: { alignItems: "center", flexDirection: "row", gap: tokens.spacing.sm, minWidth: 0 },
  routeIdentityTitle: { color: tokens.color.textMain, flexShrink: 1, fontSize: 16, fontWeight: "600", lineHeight: 22 },
  logo: { alignItems: "center", flexDirection: "row", gap: 5 },
  logoText: { color: tokens.color.textMain, fontSize: 20, fontWeight: "900", letterSpacing: -0.8 },
  logoBars: { gap: 2 },
  logoBar: { borderRadius: 2, height: 4, width: 15 },
  logoBarProtein: { backgroundColor: tokens.color.protein },
  logoBarCarbs: { backgroundColor: tokens.color.carbs },
  logoBarFat: { backgroundColor: tokens.color.fat },
  modalRoot: { flex: 1, flexDirection: "row" },
  scrim: { backgroundColor: "rgba(0,0,0,0.72)", bottom: 0, left: 0, position: "absolute", right: 0, top: 0 },
  drawer: { backgroundColor: tokens.color.surfacePage, borderRightColor: tokens.color.borderDefault, borderRightWidth: 1, height: "100%", shadowColor: "#000000", shadowOffset: { height: 0, width: 8 }, shadowOpacity: 0.45, shadowRadius: 20 },
  drawerSafeArea: { flex: 1 },
  drawerHeader: { alignItems: "center", borderBottomColor: tokens.color.borderSoft, borderBottomWidth: 1, flexDirection: "row", justifyContent: "space-between", minHeight: 64, paddingHorizontal: tokens.spacing.lg },
  closeButton: { alignItems: "center", borderRadius: tokens.radius.md, height: 44, justifyContent: "center", width: 44 },
  drawerContent: { gap: tokens.spacing.xs, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.lg },
  menuSection: { borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, gap: tokens.spacing.xs, marginTop: tokens.spacing.md, paddingTop: tokens.spacing.lg },
  menuSectionLabel: { color: tokens.color.textSoft, fontSize: tokens.type.label, fontWeight: "800", letterSpacing: 1.1, paddingHorizontal: tokens.spacing.md, paddingVertical: tokens.spacing.sm, textTransform: "uppercase" },
  drawerFooter: { alignItems: "center", borderTopColor: tokens.color.borderSoft, borderTopWidth: 1, flexDirection: "row", gap: tokens.spacing.md, padding: tokens.spacing.lg },
  accountCopy: { flex: 1, gap: 3, minWidth: 0 },
  accountName: { color: tokens.color.textMain, fontSize: 14, fontWeight: "800" },
  accountEmail: { color: tokens.color.textSoft, fontSize: 12 },
  signOutButton: { alignItems: "center", borderColor: tokens.color.borderDefault, borderRadius: tokens.radius.md, borderWidth: 1, height: 42, justifyContent: "center", width: 42 },
});
