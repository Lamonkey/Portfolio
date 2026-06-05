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
    """An OAuth 2.0 client.

    Clients arrive two ways: pre-registered via the ``register_oauth_client``
    management command, or self-registered at runtime through Dynamic Client
    Registration (RFC 7591) at ``/register``. Both paths populate the same row;
    the extra ``token_endpoint_auth_method`` / ``grant_types`` / ``response_types``
    fields exist so a DCR client (which may be public/PKCE-only or request
    refresh_token) round-trips faithfully instead of being forced back into the
    confidential-client defaults.
    """

    client_id = models.CharField(max_length=64, primary_key=True)
    client_secret = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Plaintext — see module docstring for rationale. Empty for public (PKCE-only) clients.",
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
    token_endpoint_auth_method = models.CharField(
        max_length=32,
        default="client_secret_post",
        help_text="How the client authenticates at /token: client_secret_post, client_secret_basic, or none.",
    )
    grant_types = models.JSONField(
        default=list,
        help_text="OAuth grant types the client may use. Empty falls back to ['authorization_code'].",
    )
    response_types = models.JSONField(
        default=list,
        help_text="OAuth response types the client may use. Empty falls back to ['code'].",
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
