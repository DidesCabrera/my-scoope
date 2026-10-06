#!/usr/bin/env bash
set -euo pipefail

# The Apple Product IDs are shared by StoreKit production and sandbox. The
# signed transaction environment selects the matching immutable catalog row.
python manage.py migrate --noinput
python manage.py seed_billing_catalog

for catalog_environment in live sandbox; do
  python manage.py configure_apple_catalog \
    --environment "${catalog_environment}" \
    --basic-monthly-product-id com.myscoope.basic.monthly \
    --basic-annual-product-id com.myscoope.basic.annual \
    --pro-monthly-product-id com.myscoope.pro.monthly \
    --pro-annual-product-id com.myscoope.pro.annual

  python manage.py configure_credit_pack_catalog \
    --provider apple_app_store --environment "${catalog_environment}" --offer-code credits-500 \
    --product-id com.myscoope.credits.500
  python manage.py configure_credit_pack_catalog \
    --provider apple_app_store --environment "${catalog_environment}" --offer-code credits-1000 \
    --product-id com.myscoope.credits.1000
  python manage.py configure_credit_pack_catalog \
    --provider apple_app_store --environment "${catalog_environment}" --offer-code credits-2000 \
    --product-id com.myscoope.credits.2000
done

python manage.py check --deploy
