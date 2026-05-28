"""Persistence for OAuth 2.0 clients, authorization codes, and access tokens.

This is the storage layer behind ``DjangoOAuthProvider``. Schema is deliberately
minimal — single-owner Portfolio site, manual client registration, no refresh
tokens (v1).

``client_secret`` is stored in plaintext rather than hashed. The MCP SDK's
client authenticator compares the submitted secret against ``client.client_secret``
via ``hmac.compare_digest`` (mcp/server/auth/middleware/client_auth.py), which
needs the original plaintext on the server side. The DB itself is the trust
boundary — same threat model as ``MCP_TOKEN`` living in Heroku config.
"""
from __future__ import annotations

from django.db import models
from django.utils import timezone


class OAuthClient(models.Model):
    """A pre-registered OAuth 2.0 client (e.g. Claude.ai)."""

    client_id = models.CharField(max_length=64, primary_key=True)
    client_secret = models.CharField(
        max_length=128,
        help_text="Plaintext — see module docstring for rationale.",
    )
    name = models.CharField(max_length=120, help_text="Human-friendly client name shown in logs.")
    redirect_uris = models.JSONField(
        default=list,
        help_text="Allowed redirect URIs (exact match enforced on /authorize).",
    )
    scopes = models.JSONField(
        default=list,
        help_text="Scopes this client is allowed to request. Empty means no scope restrictions.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OAuth client"
        verbose_name_plural = "OAuth clients"

    def __str__(self) -> str:
        return f"{self.name} ({self.client_id})"


class OAuthAuthCode(models.Model):
    """A short-lived authorization code redeemable at /token for an access token."""

    code = models.CharField(max_length=128, primary_key=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="auth_codes")
    redirect_uri = models.CharField(max_length=512)
    code_challenge = models.CharField(max_length=128, help_text="PKCE code_challenge (S256).")
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OAuth authorization code"
        verbose_name_plural = "OAuth authorization codes"
        indexes = [models.Index(fields=["expires_at"])]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at


class OAuthAccessToken(models.Model):
    """A bearer access token issued at /token. Validated on every /mcp request."""

    token = models.CharField(max_length=128, primary_key=True)
    client = models.ForeignKey(OAuthClient, on_delete=models.CASCADE, related_name="access_tokens")
    scopes = models.JSONField(default=list)
    expires_at = models.DateTimeField()
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OAuth access token"
        verbose_name_plural = "OAuth access tokens"
        indexes = [models.Index(fields=["expires_at"])]

    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at
