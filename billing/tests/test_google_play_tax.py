from copy import deepcopy
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from billing.application.services.google_play_tax import (
    GooglePlayTaxEvidenceError,
    prepare_google_play_tax_order,
)
from billing.infrastructure.providers.google_play import GooglePlayClient


ORDER = {
    "orderId": "GPA.1234-5678-9012-34567..0",
    "purchaseToken": "purchase-secret",
    "state": "PROCESSED",
    "buyerAddress": {"buyerCountry": "CL"},
    "createTime": "2026-11-14T14:00:00Z",
    "total": {"currencyCode": "CLP", "units": "3990", "nanos": 0},
    "tax": {"currencyCode": "CLP", "units": "637", "nanos": 0},
    "lineItems": [{
        "productId": "basic_monthly",
        "total": {"currencyCode": "CLP", "units": "3990", "nanos": 0},
        "subscriptionDetails": {
            "servicePeriodStartTime": "2026-11-14T14:00:00Z",
            "servicePeriodEndTime": "2026-12-14T14:00:00Z",
        },
    }],
}


class GooglePlayTaxOrderTests(SimpleTestCase):
    def prepare(self, order, *, kind="subscription"):
        return prepare_google_play_tax_order(
            order,
            expected_order_id=ORDER["orderId"],
            expected_product_id="basic_monthly",
            expected_purchase_token="purchase-secret",
            kind=kind,
        )

    def test_normalizes_gross_charge_without_retaining_token_or_buyer_address(self):
        result = self.prepare(ORDER)
        self.assertEqual(result["amount_minor"], 3990)
        self.assertEqual(result["period_end"], "2026-12-14T14:00:00Z")
        self.assertNotIn("purchaseToken", result)
        self.assertNotIn("buyerAddress", result)

    def test_rejects_non_chilean_pending_refunded_or_wrong_token_orders(self):
        for path, value in [
            (("state",), "PENDING"),
            (("state",), "REFUNDED"),
            (("buyerAddress", "buyerCountry"), "AR"),
            (("purchaseToken",), "other-token"),
            (("total", "currencyCode"), "USD"),
            (("total", "units"), "0"),
            (("lineItems", 0, "productId"), "other-plan"),
        ]:
            with self.subTest(path=path):
                order = deepcopy(ORDER)
                target = order
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                with self.assertRaises(GooglePlayTaxEvidenceError):
                    self.prepare(order)

    def test_requires_period_for_subscription_and_correct_kind_for_credit_pack(self):
        order = deepcopy(ORDER)
        del order["lineItems"][0]["subscriptionDetails"]["servicePeriodEndTime"]
        with self.assertRaises(GooglePlayTaxEvidenceError):
            self.prepare(order)
        with self.assertRaises(GooglePlayTaxEvidenceError):
            self.prepare(ORDER, kind="credit_pack")

    def test_credit_pack_uses_its_order_not_subscription_period(self):
        order = deepcopy(ORDER)
        del order["lineItems"][0]["subscriptionDetails"]
        order["lineItems"][0]["oneTimePurchaseDetails"] = {"quantity": 1}
        result = self.prepare(order, kind="credit_pack")
        self.assertEqual(result["kind"], "credit_pack")
        self.assertIsNone(result["period_start"])

    def test_rejects_fractional_or_inconsistent_totals(self):
        order = deepcopy(ORDER)
        order["total"]["nanos"] = 500_000_000
        with self.assertRaises(GooglePlayTaxEvidenceError):
            self.prepare(order)
        order = deepcopy(ORDER)
        order["lineItems"][0]["total"]["units"] = "3989"
        with self.assertRaises(GooglePlayTaxEvidenceError):
            self.prepare(order)

    @patch("billing.infrastructure.providers.google_play.requests.get")
    @patch.object(GooglePlayClient, "_access_token", return_value="api-token")
    def test_order_lookup_uses_server_api_and_checks_identity(self, _access_token, get):
        response = Mock(status_code=200)
        response.json.return_value = ORDER
        get.return_value = response
        client = GooglePlayClient(package_name="cl.myscoope.app", service_account={"client_email": "configured"})
        self.assertEqual(client.get_order(ORDER["orderId"])["state"], "PROCESSED")
        self.assertIn("/orders/GPA.1234-5678-9012-34567..0", get.call_args.args[0])
        response.json.return_value = {**ORDER, "orderId": "another-order"}
        with self.assertRaisesRegex(Exception, "mismatched order"):
            client.get_order(ORDER["orderId"])
