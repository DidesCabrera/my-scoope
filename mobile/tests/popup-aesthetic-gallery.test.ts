import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const source = readFileSync(new URL("../src/components/dev/popup-aesthetic-gallery.tsx", import.meta.url), "utf8");
const gallery = readFileSync(new URL("../src/app/dev/ui-gallery.tsx", import.meta.url), "utf8");
const actionSheet = readFileSync(new URL("../src/components/ui/action-sheet-modal.tsx", import.meta.url), "utf8");
const libraryActions = readFileSync(new URL("../src/components/libraries/library-actions.tsx", import.meta.url), "utf8");
const libraryListActions = readFileSync(new URL("../src/components/libraries/library-list-actions.tsx", import.meta.url), "utf8");
const account = readFileSync(new URL("../src/app/account.tsx", import.meta.url), "utf8");

test("the UI gallery presents static popup aesthetics without modal behavior", () => {
  assert.equal(source.includes("Menú inferior"), true);
  assert.equal(source.includes("Confirmación"), true);
  assert.equal(source.includes("Aviso informativo"), true);
  assert.equal(source.includes("Operación completada"), true);
  assert.equal(source.includes("<Text style={styles.actionsEyebrow}>ACCIONES</Text>"), true);
  assert.equal(source.includes("<EntityIcon entity=\"dailyPlan\" size=\"header\" />"), true);
  assert.equal(source.includes("styles.actionTable"), true);
  assert.equal(source.includes("styles.actionIcon"), false);
  assert.equal(source.includes("<Modal"), false);
  assert.equal(source.includes("onPress"), false);
  assert.equal(gallery.includes("<PopupAestheticGallery />"), true);
});

test("product action sheets blur the backdrop and preserve entity identity", () => {
  assert.equal(actionSheet.includes('import { BlurView } from "expo-blur"'), true);
  assert.equal(actionSheet.includes("nativeBlurAvailable ? <BlurView intensity={38}"), true);
  assert.equal(actionSheet.includes('<ModalBackdrop accessibilityLabel="Cerrar acciones"'), true);
  assert.equal(actionSheet.includes("sheetFrame: { backgroundColor: tokens.color.surfaceCard"), true);
  assert.equal(actionSheet.includes("actionsTable: { backgroundColor: tokens.color.surfaceMuted"), true);
  assert.equal(actionSheet.includes("marginHorizontal: tokens.layout.reducedInset - tokens.card.outerPadding"), true);
  assert.equal(actionSheet.includes("<EntityIcon entity={entity} size=\"header\" />"), true);
  assert.equal(actionSheet.includes("<View style={styles.sheetHandle} />"), true);
  assert.equal(actionSheet.includes("height: 4, marginTop: tokens.spacing.sm, width: 40"), true);
  assert.equal(actionSheet.includes("sheetBorder"), false);
  assert.equal(actionSheet.includes("actionsTable: { backgroundColor: tokens.color.surfaceMuted, borderColor"), false);
  assert.equal(actionSheet.includes('<View style={styles.actionIcon}><Icon color={color} size={18} /></View>'), true);
  assert.equal(actionSheet.includes('actionIcon: { alignItems: "center", justifyContent: "center", width: 20 }'), true);
  assert.equal(libraryActions.includes('<ActionSheetAction\n                    icon={Info}'), true);
  assert.equal(libraryActions.includes("styles.actionRow"), false);
  assert.equal(libraryActions.includes('sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 }'), true);
  assert.equal(libraryActions.includes('maxHeight: "88%"'), false);
  assert.equal(libraryActions.indexOf('<View style={styles.sheetContent}>') < libraryActions.indexOf('<ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.sheetContent}'), true);
  assert.equal(libraryListActions.includes("<ActionSheetHeader entity={entity}"), true);
  assert.equal(actionSheet.includes("<Icon color={color} size={18} />"), true);
  assert.equal(account.includes("nestedScrollEnabled"), true);
  assert.equal(account.includes("sheetScroll: { flexGrow: 0, flexShrink: 1 }"), true);
  assert.equal(account.indexOf('accountActions === "menu"') < account.indexOf("<ScrollView automaticallyAdjustKeyboardInsets contentContainerStyle={styles.sheetContent}"), true);
  assert.equal(account.includes('sheetSafeArea: { backgroundColor: tokens.color.surfaceCard, flexShrink: 1 }'), true);
});
