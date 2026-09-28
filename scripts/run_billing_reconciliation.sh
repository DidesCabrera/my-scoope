#!/usr/bin/env bash

# Run independent provider checks even when one fails, then alert through the
# cron job's non-zero exit status. Both commands remain inert until enabled.
refund_status=0
subscription_status=0

python manage.py reconcile_google_play_credit_pack_refunds --apply --if-enabled || refund_status=$?
python manage.py reconcile_google_play_subscriptions --apply --if-enabled || subscription_status=$?

if (( refund_status != 0 || subscription_status != 0 )); then
  exit 1
fi
