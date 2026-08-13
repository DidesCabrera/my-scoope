import { LibraryListScreen } from "@/components/libraries/library-list-screen";

export default function FoodsLibraryScreen() {
  return <LibraryListScreen emptyDescription="Tus alimentos personales aparecerán aquí." endpoint="/api/v1/library/foods" entity="food" title="Mis Alimentos" />;
}
