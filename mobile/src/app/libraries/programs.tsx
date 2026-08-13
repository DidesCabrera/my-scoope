import { LibraryListScreen } from "@/components/libraries/library-list-screen";

export default function ProgramsLibraryScreen() {
  return <LibraryListScreen emptyDescription="Tus programas semanales reutilizables aparecerán aquí." endpoint="/api/v1/library/programs" entity="program" title="Mis Programas Semanales" />;
}
