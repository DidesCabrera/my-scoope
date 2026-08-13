import { LibraryListScreen } from "@/components/libraries/library-list-screen";

export default function DailyPlansLibraryScreen() {
  return <LibraryListScreen emptyDescription="Tus planes diarios reutilizables aparecerán aquí." endpoint="/api/v1/library/daily-plans" entity="dailyPlan" title="Mis Planes Diarios" />;
}
