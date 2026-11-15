---
name: food-icon-scale-audit
description: Build a named 15-column comparison grid of My Scoope's published food images at current mobile size and a proposed rectangular size. Use when Felipe wants to review icon scale, transparent margins, or visual consistency before changing assets or the app.
---

# Grilla de escala visual

Use this read-only visual audit to compare the **published remote food images** together. The default output reproduces the accepted review format: 15 named images per row, first at the current 41 × 41 px title-icon frame, then in a 62 × 41 px rectangular simulation. This is a proposal preview, not an app change or publication approval.

1. Check the intended environment and the actual `FoodVisualIcon` sizes in `mobile/src/components/nutrition/food-visual-icon.tsx`. Read `docs/00_current/features/food_visual_assets.md` for the current asset contract. Pass different sizes if the code has changed.
2. Run `scripts/build_grid.py --base-url <environment-url> --output-dir <task-owned-absolute-directory>`. It reads the public visual manifest and PNGs, checks their digest and dimensions, and produces two grids and a small JSON record. It never writes to the catalog or app. Do not commit generated grids by default.
3. Inspect both grids at full resolution before showing them. State the environment, image count, and any coverage limitation. The manifest's named-image map only covers published remote assets; it is **not** an inventory of every food or emoji fallback. If named-image and ID counts diverge, stop rather than silently omit foods.
4. Present the current grid first and the rectangular simulation second. Explain that a wider UI frame alone does not enlarge a square PNG: the simulation also trims transparent outer margins and scales the visible drawing proportionally. It does not distort images or imply that 62 × 41 px has been implemented.
5. Record individual size corrections as asset-specific proposals for review. Replacing an approved asset, changing global UI dimensions, or publishing anything requires a separate explicit task and its own validation.

The generated JSON records the source URL, count, chosen sizes, and image paths so a later review can reproduce the comparison. Keep the script's network use on the selected environment only; never infer unpublished candidates from a production manifest.
