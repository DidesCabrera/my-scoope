type SupplementIntakeItem = {
  id?: number;
  supplement_id: number | null;
  supplement: Record<string, unknown>;
  quantity: string;
  unit: string;
};

export type SupplementIntake = {
  id: number;
  key: string;
  label: string;
  hour: string | null;
  status?: "planned" | "completed" | "skipped";
  items: SupplementIntakeItem[];
};

export type SupplementIntakePreset = {
  id: number;
  name: string;
  items: SupplementIntakeItem[];
};

export type Supplement = {
  id: number;
  name: string;
  brand: string;
  form: string;
  description: string;
  user_information: string;
  components: { name: string; quantity: string; unit: string }[];
  nutrition: {
    energy_kcal: string | null;
    protein_g: string | null;
    carbs_g: string | null;
    fat_g: string | null;
    saturated_fat_g: string | null;
    sugar_g: string | null;
    fiber_g: string | null;
    sodium_mg: string | null;
  };
  default_quantity: string | null;
  default_unit: string;
};
