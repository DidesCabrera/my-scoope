from django.test import SimpleTestCase, override_settings
from django.urls import reverse


class MobileAssociationTests(SimpleTestCase):
    def test_association_endpoints_fail_closed_without_signing_identity(self):
        self.assertEqual(self.client.get(reverse("apple_app_site_association")).status_code, 503)
        self.assertEqual(self.client.get(reverse("android_asset_links")).status_code, 503)

    @override_settings(MYSCOOPE_APPLE_TEAM_ID="AB12CD34EF")
    def test_apple_association_contains_only_public_share_paths(self):
        response = self.client.get(reverse("apple_app_site_association"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        details = response.json()["applinks"]["details"][0]
        self.assertEqual(details["appID"], "AB12CD34EF.com.myscoope.app")
        self.assertEqual(details["paths"], ["/s/*"])

    @override_settings(
        MYSCOOPE_ANDROID_SHA256_CERT_FINGERPRINTS=[
            ":".join(["AA"] * 32),
        ]
    )
    def test_android_association_contains_package_and_valid_fingerprint(self):
        response = self.client.get(reverse("android_asset_links"))

        self.assertEqual(response.status_code, 200)
        target = response.json()[0]["target"]
        self.assertEqual(target["package_name"], "com.myscoope.app")
        self.assertEqual(target["sha256_cert_fingerprints"], [":".join(["AA"] * 32)])
