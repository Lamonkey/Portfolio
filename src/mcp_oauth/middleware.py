"""ASGI middleware that gates ``/authorize`` behind a Django superuser session.

The MCP SDK auto-mounts ``/authorize`` as a Starlette route inside the FastMCP
streamable-HTTP app. That route does not know about Django auth, so we wrap it
with this small middleware: it reads the Django ``sessionid`` cookie, resolves
the session to a user, and only lets the request through when that user is a
``is_superuser`` admin. Anything else gets a 302 redirect to ``/admin/login/?next=…``
so the operator can log in and then bounce back into the OAuth flow.

This keeps the consent step entirely outside the Starlette / SDK layer: the
admin form lives in Django's existing admin auth, no extra password to manage,
no consent template to maintain.
"""
from __future__ import annotations

from urllib.parse import quote


class DjangoAdminGateMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if await self._is_superuser(scope):
            await self.app(scope, receive, send)
            return

        # Build a "next" URL that preserves the original /authorize query string
        # so the operator lands right back in the OAuth flow after logging in.
        raw_path: bytes = scope.get("raw_path") or scope.get("path", "").encode("utf-8")
        query: bytes = scope.get("query_string", b"")
        next_path = raw_path.decode("latin-1")
        if query:
            next_path = f"{next_path}?{query.decode('latin-1')}"

        login_url = f"/admin/login/?next={quote(next_path, safe='')}"
        await send({
            "type": "http.response.start",
            "status": 302,
            "headers": [
                (b"location", login_url.encode("latin-1")),
                (b"content-type", b"text/plain; charset=utf-8"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": b"Redirecting to Django admin login.\n",
        })

    @staticmethod
    async def _is_superuser(scope) -> bool:
        cookie_header = b""
        for name, value in scope.get("headers", []):
            if name == b"cookie":
                cookie_header = value
                break
        if not cookie_header:
            return False

        from http.cookies import SimpleCookie

        jar: SimpleCookie = SimpleCookie()
        jar.load(cookie_header.decode("latin-1"))
        morsel = jar.get("sessionid")
        if morsel is None:
            return False
        session_key = morsel.value

        from asgiref.sync import sync_to_async

        def _resolve():
            from django.contrib.auth import get_user_model
            from django.contrib.sessions.backends.db import SessionStore

            store = SessionStore(session_key=session_key)
            data = store.load()
            user_id = data.get("_auth_user_id")
            if not user_id:
                return False
            try:
                user = get_user_model().objects.get(pk=user_id)
            except get_user_model().DoesNotExist:
                return False
            return bool(user.is_active and user.is_superuser)

        return await sync_to_async(_resolve)()
