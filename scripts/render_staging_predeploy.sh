#!/usr/bin/env bash
set -euo pipefail

# Sandbox catalog IDs are deliberately scoped to staging. Production is mapped
# separately after provider-side and collection tests have passed.
python manage.py migrate --noinput
python manage.py seed_billing_catalog
python manage.py configure_paddle_catalog \
  --environment sandbox \
  --basic-product-id pro_01m29ssmvasxpvcw28anzf74t5 \
  --basic-monthly-price-id pri_01m3hzt8c4j53ez1458wc490yj \
  --basic-annual-price-id pri_01m3hzv08vhz68hcgd767dcr51 \
  --pro-product-id pro_01m29sxy39bz49ttrrrwb7dahe \
  --pro-monthly-price-id pri_01m3hzfwzvss2btdshvt199630 \
  --pro-annual-price-id pri_01m3hzgpnc4htmnr95re70r2x2
python manage.py configure_apple_catalog \
  --environment sandbox \
  --basic-monthly-product-id com.myscoope.basic.monthly \
  --basic-annual-product-id com.myscoope.basic.annual \
  --pro-monthly-product-id com.myscoope.pro.monthly \
  --pro-annual-product-id com.myscoope.pro.annual
python manage.py configure_google_play_catalog \
  --environment sandbox \
  --basic-product-id myscoope_basic \
  --pro-product-id myscoope_pro
python manage.py configure_credit_pack_catalog \
  --provider paddle --environment sandbox --offer-code credits-500 \
  --product-id pro_01m3j2az1xdcv4dgf6ayfzd619 \
  --price-id pri_01m3j2c3xm9zbvccr04cs08c6p
python manage.py configure_credit_pack_catalog \
  --provider paddle --environment sandbox --offer-code credits-1000 \
  --product-id pro_01m3j2cyyet4dynjwnvp22vnzh \
  --price-id pri_01m3j2dpxcbdd840y7cvak05tx
python manage.py configure_credit_pack_catalog \
  --provider paddle --environment sandbox --offer-code credits-2000 \
  --product-id pro_01m3j2e9wgwhsbdbcan61k9f4p \
  --price-id pri_01m3j2f8fwzat9dfacwvdd348c
python manage.py configure_credit_pack_catalog \
  --provider apple_app_store --environment sandbox --offer-code credits-500 \
  --product-id com.myscoope.credits.500
python manage.py configure_credit_pack_catalog \
  --provider apple_app_store --environment sandbox --offer-code credits-1000 \
  --product-id com.myscoope.credits.1000
python manage.py configure_credit_pack_catalog \
  --provider apple_app_store --environment sandbox --offer-code credits-2000 \
  --product-id com.myscoope.credits.2000
python manage.py configure_credit_pack_catalog \
  --provider google_play --environment sandbox --offer-code credits-500 \
  --product-id myscoope.credits.500
python manage.py configure_credit_pack_catalog \
  --provider google_play --environment sandbox --offer-code credits-1000 \
  --product-id myscoope.credits.1000
python manage.py configure_credit_pack_catalog \
  --provider google_play --environment sandbox --offer-code credits-2000 \
  --product-id myscoope.credits.2000
python manage.py check --deploy
