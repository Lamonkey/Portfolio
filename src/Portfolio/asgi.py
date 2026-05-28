"""ASGI config for Portfolio.

Composes Django with the MCP server. ``mcp_app`` exposes several routes:

- ``/mcp`` — the streamable-HTTP JSON-RPC endpoint
- ``/authorize``, ``/token``, ``/.well-known/oauth-authorization-server``,
  ``/.well-known/oauth-protected-resource`` — present only when OAuth is
  enabled via ``MCP_OAUTH_ISSUER_URL``

We mount every MCP route at top-level inside Starlette, then let everything
else fall through to Django. The ``/authorize`` route is additionally wrapped
in ``DjangoAdminGateMiddleware`` so that only a logged-in Django superuser
can approve OAuth grants. When OAuth is *not* enabled, ``/mcp`` is wrapped
in the legacy ``BearerAuthMiddleware`` instead.

See https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Portfolio.settings')

django_app = get_asgi_application()

from starlette.applications import Starlette
from starlette.routing import Mount

from mcp_oauth.middleware import DjangoAdminGateMiddleware
from mcp_server.auth import BearerAuthMiddleware
from mcp_server.server import mcp_app

_oauth_enabled = bool(os.getenv("MCP_OAUTH_ISSUER_URL"))

for _route in mcp_app.routes:
    path = getattr(_route, "path", None)
    if path == "/authorize":
        # Only Django superusers can complete the OAuth consent step.
        _route.app = DjangoAdminGateMiddleware(_route.app)
    elif path == "/mcp" and not _oauth_enabled:
        # Legacy MCP_TOKEN bearer auth — only when OAuth isn't doing it for us.
        _route.app = BearerAuthMiddleware(_route.app, os.getenv("MCP_TOKEN"))

# mcp_app's user_middleware (AuthenticationMiddleware with BearerAuthBackend,
# AuthContextMiddleware) is what wires bearer tokens into scope["user"] so the
# per-route RequireAuthMiddleware can let them through. We're pulling
# mcp_app.routes out into the outer Starlette, so we have to re-apply that
# middleware stack here or every /mcp request would 401 even with a valid
# OAuth access token. The middleware is a no-op for Django paths (it only
# acts on requests that already carry an Authorization: Bearer header).
_outer_middleware = list(getattr(mcp_app, "user_middleware", []) or [])

application = Starlette(
    routes=[
        *mcp_app.routes,
        Mount("/", app=django_app),
    ],
    middleware=_outer_middleware,
    lifespan=mcp_app.router.lifespan_context,
)
