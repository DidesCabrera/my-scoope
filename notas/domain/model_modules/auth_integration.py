"""Auth integration domain models.

This module is imported by ``notas.domain.models`` to keep the public Django
model import contract stable while reducing the size of the legacy model file.
"""

from django.contrib.auth.models import User
from django.db import models


class MCPUserToken(models.Model):
    user = models.ForeignKey(
        User,
        related_name="mcp_user_tokens",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=120)
    token_hash = models.CharField(
        max_length=64,
        unique=True,
    )
    scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def is_revoked(self):
        return self.revoked_at is not None

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


class OAuthClient(models.Model):
    client_id = models.CharField(
        max_length=120,
        unique=True,
    )
    client_name = models.CharField(max_length=160)
    redirect_uris = models.JSONField(default=list)
    allowed_scopes = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "client_name",
            "id",
        ]

    def __str__(self):
        return self.client_name

    def allows_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def allows_scope(self, scope: str) -> bool:
        return scope in self.allowed_scopes

    def allows_scopes(self, scopes: list[str]) -> bool:
        return all(
            self.allows_scope(scope)
            for scope in scopes
        )


class OAuthAuthorizationCode(models.Model):
    client = models.ForeignKey(
        OAuthClient,
        related_name="authorization_codes",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        related_name="oauth_authorization_codes",
        on_delete=models.CASCADE,
    )
    code_hash = models.CharField(
        max_length=64,
        unique=True,
    )
    redirect_uri = models.URLField(max_length=500)
    scopes = models.JSONField(default=list)
    code_challenge = models.CharField(max_length=160)
    code_challenge_method = models.CharField(max_length=20)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-created_at",
            "-id",
        ]

    def __str__(self):
        return f"OAuth code for {self.user.username} / {self.client.client_id}"

    @property
    def is_used(self):
        return self.used_at is not None


__all__ = [
    "MCPUserToken",
    "OAuthClient",
    "OAuthAuthorizationCode",
]
