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

if [[ "$MODE" != "ai" && "$MODE" != "full" && "$MODE" != "usda" && "$MODE" != "foodcatalog" && "$MODE" != "planning" && "$MODE" != "adminanalytics" && "$MODE" != "adminoperations" ]]; then
  echo "Error: modo inválido: $MODE"
  echo ""
  echo "Uso:"
  echo "  ./scripts/export_for_chatgpt.sh ai"
  echo "  ./scripts/export_for_chatgpt.sh full"
  echo "  ./scripts/export_for_chatgpt.sh usda"
  echo "  ./scripts/export_for_chatgpt.sh foodcatalog"
  echo "  ./scripts/export_for_chatgpt.sh planning"
  echo "  ./scripts/export_for_chatgpt.sh adminanalytics"
  echo "  ./scripts/export_for_chatgpt.sh adminoperations"
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
  --include '/miapp/settings/***'
  --include '/miapp/urls.py'
  --include '/miapp/asgi.py'
  --include '/miapp/wsgi.py'

  # Apps registradas en settings que Django necesita para cargar tests/comandos.
  --include '/ai_assistant/__init__.py'
  --include '/ai_assistant/apps.py'
  --include '/accounts/__init__.py'
  --include '/accounts/apps.py'
  --include '/core/__init__.py'
  --include '/core/apps.py'
  --include '/core/urls.py'
  --include '/core/views.py'

  # Script de exportación y documentación vigente.
  --include '/scripts/export_for_chatgpt.sh'
  --include '/docs/README.md'
  --include '/docs/current/README.md'
  --include '/docs/current/features/food_catalog.md'
  --include '/docs/current/features/food_catalog/***'
  --include '/docs/current/operations/export_for_chatgpt.md'
  --include '/docs/planning/***'
  --include '/docs/decisions/README.md'
  --include '/docs/decisions/*food*'
  --include '/docs/archive/food_catalog_history/***'

  # No incluye datasets externos completos. Para depurar un registro o fuente
  # puntual, adjuntar ese archivo específico o usar el modo usda.

  # App Django independiente de Food Catalog.
  --include '/food_catalog/***'
  --include '/food_catalog/tests/test_boundary_contracts.py'

  # Núcleo del app notas necesario para entender modelos y wiring.
  --include '/notas/__init__.py'
  --include '/notas/apps.py'
  --include '/notas/models.py'
  --include '/notas/admin.py'
  --include '/notas/admin_food_actions.py'
  --include '/notas/urls.py'

  --include '/notas/context_processors.py'
  --include '/notas/signals.py'
  --include '/notas/domain/***'
  --include '/notas/interface/urls/***'
  --include '/notas/interface/views/***'

  # Capas de aplicación relacionadas con Food Catalog.
  --include '/notas/application/dto/food_dto.py'
  --include '/notas/application/dto/imported_food_dto.py'
  --include '/notas/application/queries/*food*.py'
  --include '/notas/application/queries/read_boundaries.py'
  --include '/notas/application/queries/global_food_queries.py'
  --include '/notas/application/services/commands/*food*.py'
  --include '/notas/application/services/food_catalog_snapshots.py'
  --include '/notas/application/services/commands/import_usda_food_payloads.py'
  --include '/notas/application/services/food_imports/***'
  --include '/notas/application/services/nutrition/***'
  --include '/notas/application/services/cache/***'
  --include '/notas/application/services/mcp_user_tokens.py'
  --include '/notas/application/services/oauth*.py'

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

  # Tests de frontera relevantes para trabajar Food Catalog sin romper capas.
  --include '/notas/tests/test_architecture_boundaries.py'
  --include '/notas/tests/test_domain_model_boundaries.py'
  --include '/notas/tests/test_food_catalog_cycle_completion.py'
  --include '/mcp_server/tests/test_mcp_food_catalog_tool.py'
  --include '/mcp_server/tests/test_mcp_protocol_boundaries.py'

  --exclude '*'
)


PLANNING_INCLUDES=(
  # Modo focalizado para planificación estratégica y ciclos futuros.
  # Usa allowlist para compartir documentación oficial sin arrastrar código
  # productivo amplio, tests, datasets o assets pesados.
  --include '*/'

  # Contexto mínimo del proyecto.
  --include '/manage.py'
  --include '/requirements.txt'
  --include '/miapp/__init__.py'
  --include '/miapp/settings/***'
  --include '/miapp/urls.py'

  # Script de exportación y documentación oficial completa.
  --include '/scripts/export_for_chatgpt.sh'
  --include '/docs/README.md'
  --include '/docs/current/***'
  --include '/docs/decisions/***'
  --include '/docs/planning/***'

  --exclude '*'
)


ADMINANALYTICS_INCLUDES=(
  # Modo focalizado para trabajar en Admin Analytics como consola estratégica
  # independiente. Usa allowlist para iterar UI, templates, CSS, navegación,
  # selectors, services y tests del dashboard sin exportar todo el producto.
  --include '*/'

  # Contexto mínimo del proyecto Django.
  --include '/manage.py'
  --include '/requirements.txt'
  --include '/miapp/__init__.py'
  --include '/miapp/settings/***'
  --include '/miapp/urls.py'
  --include '/miapp/asgi.py'
  --include '/miapp/wsgi.py'

  # Script de exportación y documentación vigente.
  --include '/scripts/export_for_chatgpt.sh'
  --include '/docs/README.md'
  --include '/docs/current/README.md'
  --include '/docs/current/architecture/ui_patterns.md'
  --include '/docs/current/design/ui_system.md'
  --include '/docs/current/operations/export_for_chatgpt.md'
  --include '/docs/planning/README.md'
  --include '/docs/planning/product_intelligence_admin_analytics_cycle.md'
  --include '/docs/decisions/README.md'
  --include '/docs/decisions/*admin-analytics*'

  # App objetivo completa: views, urls, filtros, viewmodels, selectors,
  # services, templates y tests específicos de la consola estratégica.
  --include '/admin_analytics/***'

  # CSS propio de la consola. Se mantiene en el árbol estático actual del
  # proyecto para no duplicar pipeline estático durante esta etapa.
  --include '/notas/static/notas/css/components/admin_analytics.css'

  # Contexto mínimo de apps instaladas y modelos consumidos por selectors.
  # Esto permite revisar contratos de lectura sin exportar views/templates
  # completos de la experiencia nutricional de usuario.
  --include '/accounts/__init__.py'
  --include '/accounts/apps.py'
  --include '/accounts/models.py'
  --include '/accounts/migrations/***'
  --include '/ai_assistant/__init__.py'
  --include '/ai_assistant/apps.py'
  --include '/ai_assistant/models.py'
  --include '/ai_assistant/migrations/***'
  --include '/core/__init__.py'
  --include '/core/apps.py'
  --include '/core/models.py'
  --include '/core/urls.py'
  --include '/core/views.py'
  --include '/food_catalog/__init__.py'
  --include '/food_catalog/apps.py'
  --include '/food_catalog/models.py'
  --include '/food_catalog/migrations/***'
  --include '/notas/__init__.py'
  --include '/notas/apps.py'
  --include '/notas/models.py'
  --include '/notas/context_processors.py'
  --include '/notas/signals.py'
  --include '/notas/migrations/***'
  --include '/nutrition_solver/__init__.py'
  --include '/nutrition_solver/apps.py'
  --include '/nutrition_solver/models.py'
  --include '/nutrition_solver/domain/***'
  --include '/nutrition_solver/application/***'

  --exclude '*'
)


ADMINOPERATIONS_INCLUDES=(
  # Modo focalizado para trabajar en Admin Operations como backoffice
  # operacional independiente. Usa allowlist para corregir la nueva app,
  # planes comerciales, límites/costos, créditos, usuarios y auditoría sin
  # exportar todo el producto nutricional ni entidades editoriales completas.
  --include '*/'

  # Contexto mínimo del proyecto Django.
  --include '/manage.py'
  --include '/requirements.txt'
  --include '/miapp/__init__.py'
  --include '/miapp/settings/***'
  --include '/miapp/urls.py'
  --include '/miapp/asgi.py'
  --include '/miapp/wsgi.py'

  # Script de exportación y documentación vigente.
  --include '/scripts/export_for_chatgpt.sh'
  --include '/docs/README.md'
  --include '/docs/current/README.md'
  --include '/docs/current/architecture/ui_patterns.md'
  --include '/docs/current/design/ui_system.md'
  --include '/docs/current/operations/export_for_chatgpt.md'
  --include '/docs/planning/README.md'
  --include '/docs/planning/admin_operations_console_cycle.md'
  --include '/docs/decisions/README.md'
  --include '/docs/decisions/*admin-operations*'
  --include '/docs/decisions/*admin-analytics*'
  --include '/docs/decisions/*account*'
  --include '/docs/decisions/*credit*'
  --include '/docs/decisions/*ai-credit*'
  --include '/docs/decisions/*usage*'
  --include '/docs/decisions/*subscription*'

  # App objetivo completa: shell, workflows, audit log, templates, CSS indirecto,
  # tests y migraciones propias de Admin Operations.
  --include '/admin_operations/***'

  # CSS compartido con las consolas staff. Admin Operations reusa patrones del
  # sistema actual y puede requerir ajustes coordinados de la consola estratégica.
  --include '/notas/static/notas/css/components/admin_analytics.css'

  # Admin Analytics mínimo para revisar los bridges hacia Operations sin exportar
  # toda la consola estratégica.
  --include '/admin_analytics/__init__.py'
  --include '/admin_analytics/apps.py'
  --include '/admin_analytics/urls.py'
  --include '/admin_analytics/views.py'
  --include '/admin_analytics/viewmodels.py'
  --include '/admin_analytics/filters.py'
  --include '/admin_analytics/templates/admin_analytics/_operations_bridge.html'
  --include '/admin_analytics/templates/admin_analytics/_nav.html'
  --include '/admin_analytics/tests/__init__.py'
  --include '/admin_analytics/tests/test_operations_links.py'

  # Accounts es la dependencia principal del próximo foco: planes comerciales,
  # suscripciones, wallets, reservas, ledger, entitlements y gestión de usuarios.
  --include '/accounts/__init__.py'
  --include '/accounts/apps.py'
  --include '/accounts/admin.py'
  --include '/accounts/forms.py'
  --include '/accounts/models.py'
  --include '/accounts/urls.py'
  --include '/accounts/views.py'
  --include '/accounts/middleware.py'
  --include '/accounts/seed_plans.py'
  --include '/accounts/services/***'
  --include '/accounts/management/__init__.py'
  --include '/accounts/management/commands/__init__.py'
  --include '/accounts/management/commands/seed_account_plans.py'
  --include '/accounts/management/commands/sync_account_subscriptions.py'
  --include '/accounts/migrations/***'
  --include '/accounts/tests/__init__.py'
  --include '/accounts/tests/test_account_commercial_models.py'
  --include '/accounts/tests/test_account_credit_models.py'
  --include '/accounts/tests/test_account_entitlements.py'
  --include '/accounts/tests/test_account_plan_seed.py'
  --include '/accounts/tests/test_account_plan_seed_and_credit_services.py'
  --include '/accounts/tests/test_account_subscription_sync.py'
  --include '/accounts/tests/test_account_profile_display.py'

  # AI Assistant mínimo para límites de uso, costos/créditos y señales operativas.
  --include '/ai_assistant/__init__.py'
  --include '/ai_assistant/apps.py'
  --include '/ai_assistant/admin.py'
  --include '/ai_assistant/models.py'
  --include '/ai_assistant/application/credits.py'
  --include '/ai_assistant/application/limits.py'
  --include '/ai_assistant/application/usage.py'
  --include '/ai_assistant/application/model_routing.py'
  --include '/ai_assistant/application/reports.py'
  --include '/ai_assistant/migrations/***'
  --include '/ai_assistant/tests/__init__.py'
  --include '/ai_assistant/tests/test_account_credit_integration.py'
  --include '/ai_assistant/tests/test_ai_credits.py'
  --include '/ai_assistant/tests/test_model_routing.py'
  --include '/ai_assistant/tests/test_usage_dashboard.py'
  --include '/ai_assistant/tests/test_usage_observability.py'

  # Food Catalog mínimo porque Admin Operations V1 ya tiene workflow de curaduría.
  --include '/food_catalog/__init__.py'
  --include '/food_catalog/apps.py'
  --include '/food_catalog/models.py'
  --include '/food_catalog/migrations/***'

  # Core mínimo y modelos operacionales de notas consumidos por propuestas/auditoría.
  # Se evita exportar templates/views de edición de entidades nutricionales porque
  # no son prioridad para este nuevo foco.
  --include '/core/__init__.py'
  --include '/core/apps.py'
  --include '/core/models.py'
  --include '/core/urls.py'
  --include '/core/views.py'
  --include '/notas/__init__.py'
  --include '/notas/apps.py'
  --include '/notas/models.py'
  --include '/notas/context_processors.py'
  --include '/notas/signals.py'
  --include '/notas/migrations/***'
  --include '/notas/application/services/mcp_user_tokens.py'

  # Nutrition Solver mínimo solo para cargar settings/modelos relacionados.
  --include '/nutrition_solver/__init__.py'
  --include '/nutrition_solver/apps.py'
  --include '/nutrition_solver/models.py'
  --include '/nutrition_solver/domain/***'

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
  planning)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${PLANNING_INCLUDES[@]}")
    ;;
  adminanalytics)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${ADMINANALYTICS_INCLUDES[@]}")
    ;;
  adminoperations)
    RSYNC_EXCLUDES=("${COMMON_EXCLUDES[@]}" "${ADMINOPERATIONS_INCLUDES[@]}")
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
  planning)
    echo "planning: export focalizado para planificación estratégica. Incluye docs/current, docs/decisions, docs/planning y contexto mínimo del proyecto."
    ;;
  adminanalytics)
    echo "adminanalytics: export focalizado para Admin Analytics. Incluye la consola estratégica, CSS propio, docs del ciclo y modelos fuente mínimos."
    ;;
  adminoperations)
    echo "adminoperations: export focalizado para Admin Operations. Incluye la nueva consola operacional, auditoría, cuentas, planes comerciales, créditos, límites IA y dependencias mínimas."
    ;;
esac
echo ""
