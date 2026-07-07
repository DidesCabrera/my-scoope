from django.test import SimpleTestCase

from core.observability import FILTERED, sanitize_for_observability, sanitize_sentry_event


class ObservabilitySanitizationTests(SimpleTestCase):
    def test_sanitize_sentry_event_filters_sensitive_request_data(self):
        event = {
            "message": "ValueError in ai assistant turn",
            "request": {
                "url": "/app/ai-nutrition/intake/",
                "headers": {
                    "Authorization": "Bearer secret",
                    "Cookie": "sessionid=secret",
                },
                "data": {"prompt": "make me a meal plan"},
            },
            "extra": {
                "tool_payload": {"food": "private"},
                "safe_status": "failed",
            },
        }

        sanitized = sanitize_sentry_event(event)

        self.assertEqual(sanitized["message"], "ValueError in ai assistant turn")
        self.assertEqual(sanitized["request"]["url"], "/app/ai-nutrition/intake/")
        self.assertEqual(sanitized["request"]["headers"], FILTERED)
        self.assertEqual(sanitized["request"]["data"], FILTERED)
        self.assertEqual(sanitized["extra"]["tool_payload"], FILTERED)
        self.assertEqual(sanitized["extra"]["safe_status"], "failed")

    def test_sanitize_for_observability_filters_nested_ai_content(self):
        payload = {
            "usage": {"total_tokens": 120},
            "messages": [{"role": "user", "content": "private prompt"}],
            "tool_results": {"raw": "private data"},
            "metadata": {"provider": "openai", "api_key": "secret", "status": "error"},
        }

        sanitized = sanitize_for_observability(payload)

        self.assertEqual(sanitized["usage"]["total_tokens"], 120)
        self.assertEqual(sanitized["messages"], FILTERED)
        self.assertEqual(sanitized["tool_results"], FILTERED)
        self.assertEqual(sanitized["metadata"]["provider"], "openai")
        self.assertEqual(sanitized["metadata"]["api_key"], FILTERED)
        self.assertEqual(sanitized["metadata"]["status"], "error")
