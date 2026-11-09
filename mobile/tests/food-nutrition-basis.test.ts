import assert from "node:assert/strict";
import test from "node:test";

import { foodNutritionBasisLabel } from "../src/components/ui/food-nutrition-basis";

test("food nutrition label describes its metric basis in each context", () => {
  assert.equal(foodNutritionBasisLabel("100 g"), "Información nutricional: 100 g");
  assert.equal(foodNutritionBasisLabel("60 g"), "Información nutricional: 60 g");
  assert.equal(foodNutritionBasisLabel("1 taza (175 g)"), "Información nutricional: 175 g");
  assert.equal(foodNutritionBasisLabel("175 g (1 taza)"), "Información nutricional: 175 g");
  assert.equal(foodNutritionBasisLabel("250 ml"), "Información nutricional: 250 ml");
  assert.equal(foodNutritionBasisLabel("1 g"), "Información nutricional: 1 g");
  assert.equal(foodNutritionBasisLabel("sin medida"), null);
});
