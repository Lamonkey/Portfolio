"""ASGI config for Portfolio.

Composes Django with an MCP server mounted at /mcp. Everything else
falls through to the regular Django app.

See https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Portfolio.settings')

django_app = get_asgi_application()

from starlette.applications import Starlette
from starlette.routing import Mount

from mcp_server.auth import BearerAuthMiddleware
from mcp_server.server import mcp_app

_mcp_route = mcp_app.routes[0]
_mcp_route.app = BearerAuthMiddleware(_mcp_route.app, os.getenv("MCP_TOKEN"))

application = Starlette(
    routes=[
        _mcp_route,
        Mount("/", app=django_app),
    ],
    lifespan=mcp_app.router.lifespan_context,
)
