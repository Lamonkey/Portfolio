"""``OAuthAuthorizationServerProvider`` implementation backed by Django models.

This wires the MCP SDK's OAuth machinery to the ``mcp_oauth`` tables. The SDK
auto-mounts ``/authorize``, ``/token``, ``/.well-known/oauth-authorization-server``,
and the protected-resource metadata; this provider just owns the
authoritative storage and policy decisions behind those endpoints.

v1 scope:
- Pre-registered clients only (no Dynamic Client Registration).
- Access tokens only (no refresh tokens).
- Auto-approve at ``/authorize`` — security relies on client_secret + PKCE.
  An admin-gated consent page is a deliberate follow-up.
"""
from __future__ import annotations

import secrets
import time
from datetime import timedelta
from typing import Optional

from asgiref.sync import sync_to_async
from django.utils import timezone
from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyUrl

from .models import OAuthAccessToken, OAuthAuthCode, OAuthClient

AUTH_CODE_TTL = timedelta(minutes=10)
ACCESS_TOKEN_TTL = timedelta(days=7)


def _client_to_sdk(client: OAuthClient) -> OAuthClientInformationFull:
    """Adapt our Django model to the SDK's pydantic ``OAuthClientInformationFull``."""
    return OAuthClientInformationFull(
        client_id=client.client_id,
        client_secret=client.client_secret,
        redirect_uris=[AnyUrl(u) for u in client.redirect_uris],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code"],
        response_types=["code"],
        scope=" ".join(client.scopes) if client.scopes else None,
        client_name=client.name,
        client_id_issued_at=int(client.created_at.timestamp()),
        client_secret_expires_at=0,  # 0 = never expires per RFC 7591
    )


class DjangoOAuthProvider(OAuthAuthorizationServerProvider):
    """Provider backed by the ``mcp_oauth`` Django models."""

    async def get_client(self, client_id: str) -> Optional[OAuthClientInformationFull]:
        def _fetch():
            try:
                return OAuthClient.objects.get(pk=client_id)
            except OAuthClient.DoesNotExist:
                return None

        client = await sync_to_async(_fetch)()
        return _client_to_sdk(client) if client else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        # DCR intentionally disabled; clients are pre-registered via the
        # ``register_oauth_client`` management command.
        raise NotImplementedError(
            "Dynamic client registration is disabled for this server. "
            "Use the register_oauth_client management command."
        )

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Auto-approve and return the client's redirect URI populated with code + state.

        v1 has no consent UI — any caller that can hit /authorize with valid
        client_id + a redirect_uri that exact-matches the pre-registered set
        gets a code. The /token step still requires the client_secret.
        """
        code = "mcp_" + secrets.token_urlsafe(40)

        def _store():
            OAuthAuthCode.objects.create(
                code=code,
                client_id=client.client_id,
                redirect_uri=str(params.redirect_uri),
                code_challenge=params.code_challenge,
                scopes=params.scopes or [],
                expires_at=timezone.now() + AUTH_CODE_TTL,
            )

        await sync_to_async(_store)()

        # Build the redirect URL the SDK will 302 the browser to.
        redirect = str(params.redirect_uri)
        sep = "&" if "?" in redirect else "?"
        redirect = f"{redirect}{sep}code={code}"
        if params.state is not None:
            redirect = f"{redirect}&state={params.state}"
        return redirect

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> Optional[AuthorizationCode]:
        def _fetch():
            try:
                row = OAuthAuthCode.objects.get(pk=authorization_code, client_id=client.client_id)
            except OAuthAuthCode.DoesNotExist:
                return None
            if row.used or row.is_expired():
                return None
            return row

        row = await sync_to_async(_fetch)()
        if row is None:
            return None
        return AuthorizationCode(
            code=row.code,
            scopes=list(row.scopes or []),
            expires_at=row.expires_at.timestamp(),
            client_id=row.client_id,
            code_challenge=row.code_challenge,
            redirect_uri=AnyUrl(row.redirect_uri),
            redirect_uri_provided_explicitly=True,
        )

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        access_token = "mat_" + secrets.token_urlsafe(40)
        expires_at = timezone.now() + ACCESS_TOKEN_TTL

        def _exchange():
            # Single-use the code, even if SDK didn't already.
            OAuthAuthCode.objects.filter(pk=authorization_code.code).update(used=True)
            OAuthAccessToken.objects.create(
                token=access_token,
                client_id=client.client_id,
                scopes=authorization_code.scopes,
                expires_at=expires_at,
            )

        await sync_to_async(_exchange)()

        return OAuthToken(
            access_token=access_token,
            token_type="Bearer",
            expires_in=int(ACCESS_TOKEN_TTL.total_seconds()),
            scope=" ".join(authorization_code.scopes) if authorization_code.scopes else None,
        )

    async def load_access_token(self, token: str) -> Optional[AccessToken]:
        # 1. Real OAuth-issued access tokens (the normal path).
        def _fetch():
            try:
                row = OAuthAccessToken.objects.get(pk=token)
            except OAuthAccessToken.DoesNotExist:
                return None
            if row.is_expired():
                return None
            return row

        row = await sync_to_async(_fetch)()
        if row is not None:
            return AccessToken(
                token=row.token,
                client_id=row.client_id,
                scopes=list(row.scopes or []),
                expires_at=int(row.expires_at.timestamp()),
            )

        # 2. Legacy ``MCP_TOKEN`` fallback. Lets pre-OAuth clients (curl scripts,
        # the original BearerAuthMiddleware era) keep working during the
        # transition. Synthesised as a synthetic non-expiring admin token.
        import os

        legacy = os.getenv("MCP_TOKEN")
        if legacy and token == legacy:
            return AccessToken(
                token=token,
                client_id="legacy-mcp-token",
                scopes=[],
                expires_at=None,
            )

        return None

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> Optional[RefreshToken]:
        return None  # No refresh tokens in v1.

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        raise NotImplementedError("Refresh tokens are not issued by this server.")

    async def revoke_token(self, token) -> None:  # type: ignore[override]
        token_str = getattr(token, "token", None)
        if not token_str:
            return

        def _revoke():
            OAuthAccessToken.objects.filter(pk=token_str).delete()
            OAuthAuthCode.objects.filter(pk=token_str).delete()

        await sync_to_async(_revoke)()
