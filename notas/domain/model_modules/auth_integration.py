"""Auth integration domain models.

This module is imported by ``notas.domain.models`` to keep the public Django
model import contract stable while reducing the size of the legacy model file.
"""

import uuid

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
    device_session = models.ForeignKey(
        "OAuthDeviceSession",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_tokens",
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


class OAuthDeviceSession(models.Model):
    PLATFORM_IOS = "ios"
    PLATFORM_ANDROID = "android"
    PLATFORM_WEB = "web"
    PLATFORM_CHOICES = (
        (PLATFORM_IOS, "iOS"),
        (PLATFORM_ANDROID, "Android"),
        (PLATFORM_WEB, "Web"),
    )

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    client = models.ForeignKey(
        OAuthClient,
        on_delete=models.CASCADE,
        related_name="device_sessions",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="oauth_device_sessions",
    )
    device_id_hash = models.CharField(max_length=64)
    device_name = models.CharField(max_length=120, blank=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "user", "device_id_hash"],
                name="oauth_device_client_user_hash_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "is_active", "updated_at"],
                name="oauth_device_user_active_idx",
            ),
        ]

    def __str__(self):
        label = self.device_name or self.platform
        return f"{self.user} · {label}"


class OAuthRefreshToken(models.Model):
    session = models.ForeignKey(
        OAuthDeviceSession,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    family_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    token_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField(db_index=True)
    rotated_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["session", "family_id", "created_at"],
                name="oauth_refresh_sess_family_idx",
            ),
        ]

    def __str__(self):
        return f"Refresh token · {self.session}"


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
    "OAuthDeviceSession",
    "OAuthRefreshToken",
]
