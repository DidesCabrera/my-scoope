from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from core.memory_monitor import WorkerMemoryHighWaterMiddleware


class WorkerMemoryHighWaterMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get("/private/42/?token=secret")
        self.request.resolver_match = type("Route", (), {"view_name": "private:detail"})()
        self.response = HttpResponse("unchanged")
        self.middleware = WorkerMemoryHighWaterMiddleware(lambda request: self.response)

    @patch("core.memory_monitor.logger.warning")
    @patch("core.memory_monitor.peak_rss_mib", side_effect=(180, 200, 212, 245))
    def test_logs_only_material_increases_without_request_data(self, _peak, warning):
        for _ in range(4):
            self.assertIs(self.middleware(self.request), self.response)

        self.assertEqual(warning.call_count, 3)
        self.assertEqual(
            [call.args[2] for call in warning.call_args_list],
            [180, 212, 245],
        )
        for call in warning.call_args_list:
            self.assertEqual(call.args[3], "private:detail")
            self.assertNotIn("secret", str(call))
            self.assertNotIn("/private/42/", str(call))

    @patch("core.memory_monitor.logger.warning")
    @patch("core.memory_monitor.peak_rss_mib", return_value=192)
    def test_logs_on_exception_without_masking_it(self, _peak, warning):
        def fail(_request):
            raise ValueError("original failure")

        middleware = WorkerMemoryHighWaterMiddleware(fail)
        with self.assertRaisesMessage(ValueError, "original failure"):
            middleware(self.request)
        warning.assert_called_once()
