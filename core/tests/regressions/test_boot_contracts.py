from importlib import import_module

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import get_resolver, reverse

from core.rate_limits import limit_login, limit_signup


class BootContractRegressionTests(SimpleTestCase):
    def test_root_urlconf_imports_with_rate_limited_auth_views(self):
        """Protects local/CI boot from missing auth rate-limit dependencies."""
        urlconf = import_module(settings.ROOT_URLCONF)

        self.assertTrue(hasattr(urlconf, "urlpatterns"))
        self.assertGreater(len(urlconf.urlpatterns), 0)
        self.assertTrue(callable(limit_login))
        self.assertTrue(callable(limit_signup))

    def test_django_resolver_loads_auth_routes(self):
        """Protects the URL resolver path exercised by manage.py check/runserver."""
        resolver = get_resolver()

        self.assertGreater(len(resolver.url_patterns), 0)
        self.assertEqual(reverse("account_login"), "/accounts/login/")
        self.assertEqual(reverse("account_signup"), "/accounts/signup/")
