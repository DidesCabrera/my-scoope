import { LibraryListScreen } from "@/components/libraries/library-list-screen";

export default function MealsLibraryScreen() {
  return <LibraryListScreen emptyDescription="Tus combinaciones de alimentos reutilizables aparecerán aquí." endpoint="/api/v1/library/meals" entity="meal" title="Mis Comidas" />;
}
