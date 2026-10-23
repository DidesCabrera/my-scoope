import { LibraryListScreen } from "@/components/libraries/library-list-screen";
import { PRODUCT_VOCABULARY_ES } from "@/copy/product-vocabulary";

export default function DailyPlansLibraryScreen() {
  return <LibraryListScreen emptyDescription="Tus minutas diarias reutilizables aparecerán aquí." endpoint="/api/v1/library/daily-plans" entity="dailyPlan" title={PRODUCT_VOCABULARY_ES.dailyPlan.libraryTitle} />;
}
