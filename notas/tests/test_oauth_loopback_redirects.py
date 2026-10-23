from django.test import SimpleTestCase

from notas.domain.models import OAuthClient


class OAuthLoopbackRedirectTests(SimpleTestCase):
    def setUp(self):
        self.client = OAuthClient(
            redirect_uris=[
                "http://127.0.0.1:64173/callback/codex?source=mcp",
                "https://chatgpt.com/connector/oauth/callback",
            ],
        )

    def test_accepts_another_loopback_port_with_exact_host_path_and_query(self):
        self.assertTrue(
            self.client.allows_redirect_uri(
                "http://127.0.0.1:49830/callback/codex?source=mcp"
            )
        )

    def test_preserves_exact_match_for_non_loopback_redirects(self):
        self.assertTrue(
            self.client.allows_redirect_uri(
                "https://chatgpt.com/connector/oauth/callback"
            )
        )

    def test_rejects_every_change_other_than_the_loopback_port(self):
        for uri in (
            "http://localhost:49830/callback/codex?source=mcp",
            "http://127.0.0.2:49830/callback/codex?source=mcp",
            "https://127.0.0.1:49830/callback/codex?source=mcp",
            "http://127.0.0.1:49830/callback/other?source=mcp",
            "http://127.0.0.1:49830/callback/codex?source=other",
            "http://127.0.0.1:49830/callback/codex?source=mcp#fragment",
            "http://user@127.0.0.1:49830/callback/codex?source=mcp",
            "http://127.0.0.1:0/callback/codex?source=mcp",
            "http://127.0.0.1:invalid/callback/codex?source=mcp",
            "http://127.0.0.1/callback/codex?source=mcp",
            "https://chatgpt.com:49830/connector/oauth/callback",
        ):
            with self.subTest(uri=uri):
                self.assertFalse(self.client.allows_redirect_uri(uri))
