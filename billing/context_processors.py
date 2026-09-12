from billing.presentation.public_catalog import build_public_plan_prices


def public_billing_catalog(request):
    """Expose canonical prices only where the public landing template needs them."""

    if request.path != "/":
        return {}
    return {"pricing": build_public_plan_prices()}
