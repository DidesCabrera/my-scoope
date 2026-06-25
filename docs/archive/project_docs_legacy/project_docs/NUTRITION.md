# NUTRITION

Nutrition logic is energy-based, not weight-based.

Rules:
- Protein: 4 kcal/g
- Carbs: 4 kcal/g
- Fat: 9 kcal/g

Allocation (alloc) is always based on kcal contribution, never grams.

Allocations exist at multiple levels:
- Food alloc (within itself)
- Meal alloc (macro distribution)
- Relative alloc (food contribution to macro total)

All nutrition is calculated dynamically, never persisted.