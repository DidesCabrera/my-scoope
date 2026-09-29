from django.db import migrations

PRICE_TRANSITION = {
    "basic-monthly": (7990, 3990),
    "basic-annual": (79900, 34990),
    "pro-monthly": (12990, 6990),
    "pro-annual": (129900, 59990),
}


def transition_prices(apps, schema_editor):
    Offer = apps.get_model("billing", "BillingOffer")
    Product = apps.get_model("billing", "BillingProduct")
    for code, (old_amount, new_amount) in PRICE_TRANSITION.items():
        offer = Offer.objects.filter(code=code).first()
        if offer is None or offer.amount_minor != old_amount or offer.currency != "CLP":
            continue
        # Historical provider snapshots remain intact. They cannot sell the
        # superseded price after the canonical offer changes.
        Product.objects.filter(offer_id=offer.pk, active=True).update(active=False)
        offer.amount_minor = new_amount
        offer.save(update_fields=["amount_minor", "updated_at"])


class Migration(migrations.Migration):
    dependencies = [("billing", "0004_commercial_offer_catalog")]

    operations = [migrations.RunPython(transition_prices, migrations.RunPython.noop)]
