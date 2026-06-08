#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-ai}"

PROJECT_DIR="$(pwd)"
PARENT_DIR="$(dirname "$PROJECT_DIR")"

EXPORT_BASE_NAME="proyecto_django_export"
EXPORT_NAME="${EXPORT_BASE_NAME}_${MODE}"
EXPORT_DIR="$PARENT_DIR/$EXPORT_NAME"
ZIP_PATH="$PARENT_DIR/$EXPORT_NAME.zip"

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
  echo "Error: ejecuta este script desde la raíz del proyecto Django, donde está manage.py"
  exit 1
fi

if [[ "$MODE" != "ai" && "$MODE" != "full" && "$MODE" != "usda" ]]; then
  echo "Error: modo inválido: $MODE"
  echo ""
  echo "Uso:"
  echo "  ./scripts/export_for_chatgpt.sh ai"
  echo "  ./scripts/export_for_chatgpt.sh full"
  echo "  ./scripts/export_for_chatgpt.sh usda"
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
esac

rsync -av \
  "${RSYNC_EXCLUDES[@]}" \
  "$PROJECT_DIR/" "$EXPORT_DIR/"

cd "$PARENT_DIR"

find "$EXPORT_NAME" -name ".DS_Store" -delete
find "$EXPORT_NAME" -name "__pycache__" -type d -exec rm -rf {} +
find "$EXPORT_NAME" -name "*.pyc" -delete

zip -r -q "$ZIP_PATH" "$EXPORT_NAME" \
  -x "*.DS_Store" \
  -x "__MACOSX/*" \
  -x "*/__pycache__/*"

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
esac
echo ""