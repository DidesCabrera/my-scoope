import { StyleSheet, Text } from "react-native";

type FoodVisual = { emoji: string; visualKey: string };

const nameRules: readonly [readonly string[], FoodVisual][] = [
  [["maca", "polvo"], { emoji: "🥣", visualKey: "maca_powder" }],
  [["maca"], { emoji: "🌱", visualKey: "maca_root" }],
  [["pechuga", "pollo"], { emoji: "🍗", visualKey: "chicken_breast" }],
  [["pechuga", "pavo"], { emoji: "🍗", visualKey: "turkey_breast" }],
  [["pollo"], { emoji: "🍗", visualKey: "chicken" }],
  [["pavo"], { emoji: "🍗", visualKey: "turkey" }],
  [["pato"], { emoji: "🦆", visualKey: "duck" }],
  [["huevo"], { emoji: "🥚", visualKey: "egg" }],
  [["manzana"], { emoji: "🍎", visualKey: "apple" }],
  [["pera"], { emoji: "🍐", visualKey: "pear" }],
  [["platano"], { emoji: "🍌", visualKey: "banana" }],
  [["banana"], { emoji: "🍌", visualKey: "banana" }],
  [["naranja"], { emoji: "🍊", visualKey: "orange" }],
  [["mandarina"], { emoji: "🍊", visualKey: "mandarin" }],
  [["limon"], { emoji: "🍋", visualKey: "lemon" }],
  [["sandia"], { emoji: "🍉", visualKey: "watermelon" }],
  [["melon"], { emoji: "🍈", visualKey: "melon" }],
  [["uva"], { emoji: "🍇", visualKey: "grapes" }],
  [["frutilla"], { emoji: "🍓", visualKey: "strawberry" }],
  [["fresa"], { emoji: "🍓", visualKey: "strawberry" }],
  [["arandano"], { emoji: "🫐", visualKey: "blueberry" }],
  [["cereza"], { emoji: "🍒", visualKey: "cherry" }],
  [["durazno"], { emoji: "🍑", visualKey: "peach" }],
  [["mango"], { emoji: "🥭", visualKey: "mango" }],
  [["pina"], { emoji: "🍍", visualKey: "pineapple" }],
  [["coco"], { emoji: "🥥", visualKey: "coconut" }],
  [["kiwi"], { emoji: "🥝", visualKey: "kiwi" }],
  [["palta"], { emoji: "🥑", visualKey: "avocado" }],
  [["aguacate"], { emoji: "🥑", visualKey: "avocado" }],
  [["tomate"], { emoji: "🍅", visualKey: "tomato" }],
  [["berenjena"], { emoji: "🍆", visualKey: "eggplant" }],
  [["papa"], { emoji: "🥔", visualKey: "potato" }],
  [["camote"], { emoji: "🍠", visualKey: "sweet_potato" }],
  [["zanahoria"], { emoji: "🥕", visualKey: "carrot" }],
  [["choclo"], { emoji: "🌽", visualKey: "corn" }],
  [["maiz"], { emoji: "🌽", visualKey: "corn" }],
  [["aji"], { emoji: "🌶️", visualKey: "chili_pepper" }],
  [["pimenton"], { emoji: "🫑", visualKey: "bell_pepper" }],
  [["pepino"], { emoji: "🥒", visualKey: "cucumber" }],
  [["brocoli"], { emoji: "🥦", visualKey: "broccoli" }],
  [["coliflor"], { emoji: "🥦", visualKey: "cauliflower" }],
  [["ajo"], { emoji: "🧄", visualKey: "garlic" }],
  [["cebolla"], { emoji: "🧅", visualKey: "onion" }],
  [["champinon"], { emoji: "🍄", visualKey: "mushroom" }],
  [["mani"], { emoji: "🥜", visualKey: "peanut" }],
  [["almendra"], { emoji: "🌰", visualKey: "almond" }],
  [["nuez"], { emoji: "🌰", visualKey: "walnut" }],
  [["poroto"], { emoji: "🫘", visualKey: "beans" }],
  [["frijol"], { emoji: "🫘", visualKey: "beans" }],
  [["lenteja"], { emoji: "🫘", visualKey: "lentils" }],
  [["garbanzo"], { emoji: "🫘", visualKey: "chickpeas" }],
  [["arveja"], { emoji: "🫛", visualKey: "peas" }],
  [["arroz"], { emoji: "🍚", visualKey: "rice" }],
  [["avena"], { emoji: "🥣", visualKey: "oats" }],
  [["pan"], { emoji: "🍞", visualKey: "bread" }],
  [["leche"], { emoji: "🥛", visualKey: "milk" }],
  [["yogur"], { emoji: "🥣", visualKey: "yogurt" }],
  [["queso"], { emoji: "🧀", visualKey: "cheese" }],
  [["mantequilla"], { emoji: "🧈", visualKey: "butter" }],
  [["salmon"], { emoji: "🐟", visualKey: "salmon" }],
  [["atun"], { emoji: "🐟", visualKey: "tuna" }],
  [["camaron"], { emoji: "🦐", visualKey: "shrimp" }],
  [["pulpo"], { emoji: "🐙", visualKey: "octopus" }],
  [["calamar"], { emoji: "🦑", visualKey: "squid" }],
  [["cerdo"], { emoji: "🥩", visualKey: "pork" }],
  [["vacuno"], { emoji: "🥩", visualKey: "beef" }],
  [["carne"], { emoji: "🥩", visualKey: "meat" }],
  [["aceite"], { emoji: "🫒", visualKey: "oil" }],
  [["aceituna"], { emoji: "🫒", visualKey: "olive" }],
];

const genericVisual: FoodVisual = { emoji: "🍽️", visualKey: "food_generic" };

function normalizeFoodName(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase("es")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

export function inferFoodVisual(name: string): FoodVisual {
  const normalized = ` ${normalizeFoodName(name)} `;
  return nameRules.find(([terms]) => terms.every((term) => normalized.includes(` ${term} `)))?.[1] ?? genericVisual;
}

export function resolveFoodVisual(name: string, emoji?: string | null, visualKey?: string | null): FoodVisual {
  const inferred = inferFoodVisual(name);
  return {
    emoji: emoji?.trim() || inferred.emoji,
    visualKey: visualKey?.trim() || inferred.visualKey,
  };
}

export function FoodVisualIcon({ emoji, name, size = "compact", visualKey }: { emoji?: string | null; name: string; size?: "compact" | "panel" | "title"; visualKey?: string | null }) {
  const visual = resolveFoodVisual(name, emoji, visualKey);
  return (
    <Text
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[styles.icon, size === "panel" && styles.panelIcon, size === "title" && styles.titleIcon]}>
      {visual.emoji}
    </Text>
  );
}

const styles = StyleSheet.create({
  icon: { flexShrink: 0, fontSize: 18, lineHeight: 22, textAlign: "center", width: 24 },
  panelIcon: { fontSize: 14, lineHeight: 18, width: 20 },
  titleIcon: { fontSize: 22, lineHeight: 28, width: 29 },
});
