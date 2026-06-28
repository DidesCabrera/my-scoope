#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-ai}"

PROJECT_DIR="$(pwd -P)"
PARENT_DIR="$(dirname "$PROJECT_DIR")"

EXPORT_BASE_NAME="proyecto_django_export"
EXPORT_NAME="${EXPORT_BASE_NAME}_${MODE}"
EXPORT_DIR="$PARENT_DIR/$EXPORT_NAME"
ZIP_PATH="$PARENT_DIR/$EXPORT_NAME.zip"

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
  echo "Error: ejecuta este script desde la raíz del proyecto Django, donde está manage.py"
  exit 1
fi

if [[ "$MODE" != "ai" && "$MODE" != "full" && "$MODE" != "usda" && "$MODE" != "foodcatalog" ]]; then
  echo "Error: modo inválido: $MODE"
  echo ""
  echo "Uso:"
  echo "  ./scripts/export_for_chatgpt.sh ai"
  echo "  ./scripts/export_for_chatgpt.sh full"
  echo "  ./scripts/export_for_chatgpt.sh usda"
  echo "  ./scripts/export_for_chatgpt.sh foodcatalog"
  exit 1
fi

if [[ "$(basename "$PROJECT_DIR")" == "$EXPORT_NAME" ]]; then
  echo "Error: este script no debe ejecutarse desde una carpeta exportada llamada $EXPORT_NAME"
  echo "Ejecuta el script desde la raíz real del repo, no desde un ZIP descomprimido de exportación."
  exit 1
fi

echo ""
echo "Generando ZIP optimizado para ChatGPT"
echo "Modo: $MODE"
echo ""

rm -rf "$EXPORT_DIR"
rm -f "$ZIP_PATH"

COMMON_EXCLUDES=(
  --exclude '.git/'
  --exclude '.github/'
  --exclude '.idea/'
  --exclude '.vscode/'

  # Notas personales del desarrollador humano.
  # No forman parte de la documentación oficial ni deben alimentar análisis de IA.
  --exclude 'manual_docs/'

  --exclude '__pycache__/'
  --exclude '*.pyc'
  --exclude '*.pyo'

  --exclude '.pytest_cache/'
  --exclude '.mypy_cache/'
  --exclude '.ruff_cache/'
  --exclude '.coverage'
  --exclude 'htmlcov/'

  --exclude '.DS_Store'
  --exclude '__MACOSX/'

  --exclude 'venv/'
  --exclude '.venv/'
  --exclude 'env/'

  --exclude '.env'
  --exclude '.env.*'
  --exclude '!/.env.example'

  --exclude 'db.sqlite3'
  --exclude '*.sqlite3'
  --exclude '*.db'

  --exclude 'staticfiles/'
  --exclude 'media/'

  --exclude 'node_modules/'
  --exclude 'dist/'
  --exclude 'build/'

  --exclude '*.zip'
  --exclude '*.tar'
  --exclude '*.tar.gz'

  --exclude '*.log'
  --exclude '*.patch'
  --exclude '*.bak'
  --exclude '*.tmp'
  --exclude '*.orig'
  --exclude '*.rej'
  --exclude '*.swp'
  --exclude '*.swo'

  --exclude 'tmp/'
  --exclude 'temp/'

  # Imágenes/assets pesados.
  # Normalmente no son necesarios para comprender la arquitectura o lógica del proyecto.
  --exclude 'static/img/'
  --exclude 'notas/static/notas/img/'
  --exclude '*.jpg'
  --exclude '*.jpeg'
  --exclude '*.png'
  --exclude '*.webp'
  --exclude '*.gif'
  --exclude '*.ico'
  --exclude '*.svg'
)

AI_EXCLUDES=(
  # Tests excluidos en modo ai para reducir ruido y tokens.
  --exclude '*/tests/'
  --exclude 'tests/'
  --exclude 'test_*.py'
  --exclude '*_test.py'

  # USDA excluido en modo ai.
  --exclude 'data/food_sources/'
)

FULL_EXCLUDES=(
  # En modo full se mantienen los tests,
  # pero USDA sigue excluido porque es fuente de datos externa pesada.
  --exclude 'data/food_sources/'
)

USDA_EXCLUDES=(
  # En modo usda se incluye data/food_sources/,
  # por lo que no se excluye USDA.
  # Se mantienen excluidas las imágenes/assets pesados.
)

FOODCATALOG_INCLUDES=(
  # Modo focalizado para trabajar en Food Catalog App como subsistema separado.
  # Usa allowlist: se incluyen solo rutas relevantes para catálogo, fuentes,
  # importación, curaduría, normalización y contrato hacia el core nutricional.
  --include '*/'

  # Contexto mínimo del proyecto Django.
  --include '/manage.py'
  --include '/requirements.txt'
  --include '/miapp/__init__.py'
  --include '/miapp/settings.py'
  --include '/miapp/urls.py'
  --include '/miapp/asgi.py'
  --include '/miapp/wsgi.py'

  # Script de exportación y documentación vigente.
  --include '/scripts/export_for_chatgpt.sh'
  --include '/docs/README.md'
  --include '/docs/current/README.md'
  --include '/docs/current/features/food_catalog.md'
  --include '/docs/current/features/food_catalog/***'
  --include '/docs/current/operations/export_for_chatgpt.md'
  --include '/docs/decisions/README.md'
  --include '/docs/decisions/*food*'
  --include '/docs/archive/food_catalog_history/***'

  # No incluye datasets externos completos. Para depurar un registro o fuente
  # puntual, adjuntar ese archivo específico o usar el modo usda.

  # Núcleo del app notas necesario para entender modelos y wiring.
  --include '/notas/__init__.py'
  --include '/notas/apps.py'
  --include '/notas/models.py'
  --include '/notas/admin.py'
  --include '/notas/admin_food_actions.py'
  --include '/notas/urls.py'

  # Capas de aplicación relacionadas con Food Catalog.
  --include '/notas/application/dto/food_dto.py'
  --include '/notas/application/dto/imported_food_dto.py'
  --include '/notas/application/queries/*food*.py'
  --include '/notas/application/queries/global_food_queries.py'
  --include '/notas/application/services/commands/*food*.py'
  --include '/notas/application/services/commands/import_usda_food_payloads.py'
  --include '/notas/application/services/food_imports/***'
  --include '/notas/application/services/nutrition/food_aggregation.py'

  # Commands internos de importación, exportación y curaduría.
  --include '/notas/management/__init__.py'
  --include '/notas/management/commands/__init__.py'
  --include '/notas/management/commands/*food*.py'
  --include '/notas/management/commands/*usda*.py'
  --include '/notas/management/commands/apply_core_food_seed.py'
  --include '/notas/management/commands/promote_initial_core_foods.py'

  # Migraciones: se conservan todas porque los modelos están en un único app
  # Django y varias relaciones históricas alimentan el estado real de Food.
  --include '/notas/migrations/***'

  # Interfaz actual relacionada con Food. Útil para comprender el contrato
  # que Food Catalog entrega al entorno de gestión nutricional.
  --include '/notas/interface/routing/food.py'
  --include '/notas/interface/urls/foods.py'
  --include '/notas/interface/views/foods.py'
  --include '/notas/interface/views/meal_foods.py'
  --include '/notas/presentation/actions/*food*.py'
  --include '/notas/presentation/composition/forms/form_food_builder.py'
  --include '/notas/presentation/composition/js/*food*.py'
  --include '/notas/presentation/composition/viewmodel/food/***'
  --include '/notas/presentation/frontend/jscontext/*food*.py'
  --include '/notas/presentation/pages/food_pages.py'
  --include '/notas/presentation/routing/food.py'
  --include '/notas/presentation/viewmodels/content/food/***'
  --include '/notas/templates/components/*food*.html'
  --include '/notas/templates/components/*foods*.html'
  --include '/notas/templates/notas/foods/***'
  --include '/notas/templates/notas/admin/food_catalog.html'
  --include '/notas/static/notas/js/*food*.js'

  # Tests y fixtures alimentarios.
  --include '/notas/tests/fixtures/food_imports/***'
  --include '/notas/tests/test_*food*.py'
  --include '/notas/tests/test_*usda*.py'
  --include '/notas/tests/test_apply_core_food_seed_command.py'
  --include '/notas/tests/test_core_food_seed_catalog.py'
  --include '/notas/tests/test_core_food_seed_service.py'
  --include '/notas/tests/test_global_food_queries.py'

  --exclude '*'
)

case "$MODE" in
  ai)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${AI_EXCLUDES[@]}")
    ;;
  full)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${FULL_EXCLUDES[@]}")
    ;;
  usda)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${USDA_EXCLUDES[@]}")
    ;;
  foodcatalog)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${FOODCATALOG_INCLUDES[@]}")
    ;;
esac

rsync -av \
  "${RSYNC_EXCLUDES[@]}" \
  "$PROJECT_DIR/" "$EXPORT_DIR/"

cd "$PARENT_DIR"

find "$EXPORT_NAME" -name ".DS_Store" -delete
find "$EXPORT_NAME" -name "__pycache__" -type d -exec rm -rf {} +
find "$EXPORT_NAME" -name "*.pyc" -delete
find "$EXPORT_NAME" -name "*.orig" -delete
find "$EXPORT_NAME" -name "*.rej" -delete

zip -r -q "$ZIP_PATH" "$EXPORT_NAME" \
  -x "*.DS_Store" \
  -x "__MACOSX/*" \
  -x "*/__pycache__/*" \
  -x "*.orig" \
  -x "*.rej"

echo ""
echo "ZIP generado correctamente:"
echo "$ZIP_PATH"
echo ""
echo "Tamaño:"
du -h "$ZIP_PATH"
echo ""
echo "Archivos incluidos:"
find "$EXPORT_DIR" -type f | wc -l
echo ""
echo "Archivos más grandes incluidos:"
find "$EXPORT_DIR" -type f -exec du -h {} + | sort -hr | head -10
echo ""
echo "Modo generado:"
case "$MODE" in
  ai)
    echo "ai: uso normal para compartir código conmigo. Excluye USDA, imágenes y tests."
    ;;
  full)
    echo "full: mantiene tests. Excluye USDA e imágenes."
    ;;
  usda)
    echo "usda: incluye USDA y tests. Excluye imágenes."
    ;;
  foodcatalog)
    echo "foodcatalog: export focalizado para Food Catalog App. Incluye importadores, curaduría, docs y tests relacionados. Excluye datasets externos completos."
    ;;
esac
echo ""