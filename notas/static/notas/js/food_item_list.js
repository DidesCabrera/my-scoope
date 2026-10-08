import { getFoodKcal } from "./food_math.js";
import {
  escapeHtml,
  renderPickerResultBadges,
  renderPickerResultKpis,
  renderPickerResultTitle,
} from "./picker_result_components.js";

function getFoodDisplayName(food) {
  return food?.display_name || food?.name || "";
}

function shouldShowOriginalName(food) {
  const displayName = getFoodDisplayName(food);
  const originalName = food?.name || "";

  return Boolean(
    displayName &&
    originalName &&
    displayName !== originalName
  );
}

function normalizeSourceLabel(source) {
  if (!source) return "";

  const normalized = String(source).toLowerCase();

  if (normalized === "usda") return "USDA";
  if (normalized === "open_food_facts") return "Open Food Facts";
  if (normalized === "latinfoods") return "LATINFOODS";
  if (normalized === "inta_chile") return "INTA Chile";
  if (normalized === "manual") return "Manual";
  if (normalized === "global") return "Global";
  if (normalized === "system") return "Sistema";
  if (normalized === "user") return "Usuario";

  return String(source)
    .replaceAll("_", " ")
    .replace(/\b\w/g, char => char.toUpperCase());
}

function resolvePrimaryBadge(food) {
  if (food?.is_user_food) {
    return {
      label: food.picker_label || "Tu alimento",
      modifier: "user"
    };
  }

  if (food?.is_global_food) {
    return {
      label: food.picker_label || "Global",
      modifier: "global"
    };
  }

  if (food?.picker_label) {
    return {
      label: food.picker_label,
      modifier: "system"
    };
  }

  return null;
}

function buildBadges(food) {
  const badges = [];

  const primaryBadge = resolvePrimaryBadge(food);
  if (primaryBadge) {
    badges.push(primaryBadge);
  }

  if (food?.is_verified) {
    badges.push({
      label: "Verificado",
      modifier: "verified"
    });
  }

  const sourceLabel = normalizeSourceLabel(food?.source);
  const shouldShowSource =
    sourceLabel &&
    !["Usuario", "Global", "Sistema"].includes(sourceLabel);

  if (shouldShowSource) {
    badges.push({
      label: sourceLabel,
      modifier: "source"
    });
  }

  if (food?.visibility === "core") {
    badges.push({
      label: "Core",
      modifier: "core"
    });
  }

  return badges;
}

export function renderFoodItem(food) {
  if (!food || !food.name) return "";

  const displayName = getFoodDisplayName(food);
  const kcal = getFoodKcal(food);

  return `
    <div class="picker-item picker-result picker-result--food">

      ${renderPickerResultTitle({
        name: displayName,
        icon: "carrot",
        iconClass: "food",
        badges: buildBadges(food),
        unitLabel: `100${food.quantity_unit || "g"}`,
      })}

      ${renderPickerResultKpis({
        kcal,
        protein: food.protein,
        carbs: food.carbs,
        fat: food.fat,
        alloc: food.alloc,
      })}

    </div>
  `;
}
