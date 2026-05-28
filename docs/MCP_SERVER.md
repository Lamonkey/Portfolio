# MCP Server

## Overview

The portfolio ships an embedded [Model Context Protocol](https://modelcontextprotocol.io) server that exposes CRUD access to the `Project` model. It lets MCP-capable LLM clients (Claude Desktop, Claude Code, the MCP Inspector, etc.) browse and modify the projects in your portfolio as a structured data source instead of scraping the rendered HTML.

The server lives in [`src/mcp_server/`](../src/mcp_server) and is mounted into the ASGI app at the path **`/mcp`** (no trailing slash — that's what FastMCP's `streamable_http_app()` registers by default).

## Architecture

The Django app and the MCP server are composed at the ASGI layer using Starlette as the outer router:

```
        ┌──────────────────────────────────────────────┐
        │  Starlette (Portfolio.asgi:application)      │
        │                                              │
        │   /mcp   ──►  BearerAuthMiddleware           │
        │                    └─►  FastMCP streamable   │
        │                              HTTP app        │
        │                                              │
        │   /      ──►  Django (get_asgi_application)  │
        └──────────────────────────────────────────────┘
```

Wired in [`src/Portfolio/asgi.py`](../src/Portfolio/asgi.py):

- `mcp_server.server.mcp_app` is a FastMCP `streamable_http_app()` — a Starlette sub-app speaking JSON-RPC 2.0 over the [streamable HTTP transport](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http).
- The single route inside `mcp_app` is wrapped in `BearerAuthMiddleware` so every request to `/mcp` must present a valid bearer token before it reaches the JSON-RPC handler.
- Everything else falls through to the regular Django WSGI/ASGI app mounted at `/`.

Because the entrypoint is ASGI, the app is started with `uvicorn` (see [`Procfile`](../Procfile)), not `gunicorn`. The `python manage.py runserver` dev command works for the Django side but does **not** serve the `/mcp` route — for end-to-end MCP testing you need to run uvicorn directly (see [Local testing](#local-testing) below).

## Exposed tools

Defined in [`src/mcp_server/server.py`](../src/mcp_server/server.py) using the FastMCP `@mcp.tool()` decorator. The server is initialised as `FastMCP("portfolio", stateless_http=True)` — `stateless_http=True` means each HTTP request is a self-contained JSON-RPC call with no server-side session.

| Tool | Args | Returns | Description |
|---|---|---|---|
| `list_projects` | none | `list[dict]` | Every `Project` row ordered newest-first. Summary fields (incl. `subtitle`) only — `description` and `meta_description` are omitted to keep responses small. |
| `get_project` | `project_id: int` | `dict` | Full details for one project including the raw markdown `description` and `meta_description`. Raises `ValueError` if no project has that id. |
| `create_project` | `title: str`, optional `subtitle`, `type`, `link`, `github_link`, `description`, `meta_description` | `dict` | Creates a new project and returns its full details (including the assigned `id`). Image upload is **not** supported via MCP — the project is created without an image (`image_url` will be `null`). |
| `update_project` | `project_id: int`, optional `title`, `subtitle`, `type`, `link`, `github_link`, `description`, `meta_description` | `dict` | Partial update — only fields explicitly passed (non-null) are written; everything else is left untouched. To clear a field, pass an empty string. Raises `ValueError` if no project has that id. |
| `delete_project` | `project_id: int` | `dict` | Deletes the project. Returns `{"deleted": true, "id": ..., "title": ...}` for confirmation. Raises `ValueError` if no project has that id. |

### Field semantics

- **`title`** — display name, max 64 chars.
- **`subtitle`** — short one-liner shown on the list-page card (max 200 chars). If empty, the card falls back to a truncated `description`.
- **`description`** — long-form markdown rendered on the detail page. The "story" of the project.
- **`meta_description`** — SEO snippet (max 160 chars) used in `<meta name="description">`, `og:description`, and `twitter:description`. If empty, falls back to `subtitle`, then to a truncated `description`.

All tools wrap synchronous ORM calls in `asgiref.sync.sync_to_async` so they don't block the event loop.

### A note on images

Adding an image to a project requires uploading a file, which doesn't fit the JSON-RPC request shape cleanly. The MCP tools deliberately don't expose image upload — projects created via MCP have no image until you add one through the Django admin or a separate workflow. The existing [`create_test_projects` management command](CREATE_TEST_PROJECTS.md) shows the pattern for adding images programmatically (downloads from Picsum, attaches via `project.image.save(...)`).

### Project dict shape

```python
{
    "id": int,
    "title": str,
    "subtitle": str,                # may be empty
    "type": str,
    "link": str | None,
    "github_link": str | None,
    "image_url": str | None,        # signed S3 URL if AWS storage is configured, else local path
    "description": str,             # only present from get_project / create_project / update_project
    "meta_description": str,        # only present from get_project / create_project / update_project
}
```

`image_url` is `None` when the project has no image *or* when accessing `project.image.url` raises `ValueError` (e.g. the file is missing from storage).

## Authentication

`/mcp` is protected by [`BearerAuthMiddleware`](../src/mcp_server/auth.py). Every request must include:

```
Authorization: Bearer <token>
```

The expected token is read from the `MCP_TOKEN` environment variable at startup.

| Condition | Response |
|---|---|
| `MCP_TOKEN` env var is unset or empty | `503 Service Unavailable` with body `MCP_TOKEN is not configured on the server.` |
| `Authorization` header missing or token mismatch | `401 Unauthorized` with `WWW-Authenticate: Bearer realm="mcp"` |
| Token matches | Request is forwarded to the FastMCP app |

The middleware only enforces auth on `scope["type"] == "http"`. Non-HTTP scopes (lifespan startup/shutdown events) pass through unchanged.

## Configuration

The server reads these environment variables:

| Env var | Required | Purpose |
|---|---|---|
| `MCP_TOKEN` | yes | Legacy bearer token. Required for the curl/Inspector flow. Also accepted by the OAuth-mode server as a fallback (see Authentication modes below). |
| `MCP_ALLOWED_HOSTS` | yes in production | Comma-separated `Host` header values to allow past FastMCP's DNS-rebinding protection. Local dev works without this (FastMCP defaults to allowing localhost). In production you **must** set this or every request will get a 421 "Invalid Host header". |
| `MCP_ALLOWED_ORIGINS` | only for browser clients | Comma-separated `Origin` header values for browser-based MCP clients (e.g. the Inspector running on a non-localhost URL). Non-browser clients like Claude Desktop don't send Origin and don't need this. |
| `MCP_OAUTH_ISSUER_URL` | yes for OAuth mode | When set, turns on OAuth 2.0. Value is the public base URL of this server (e.g. `https://lamonkey-portfolio.herokuapp.com`). FastMCP uses it to populate the `issuer` field in `/.well-known/oauth-authorization-server` and to auto-mount the `/authorize`, `/token`, and well-known metadata endpoints. |
| `MCP_OAUTH_RESOURCE_URL` | optional | Defaults to `MCP_OAUTH_ISSUER_URL`. Override if the resource server URL differs from the issuer URL. |

Example `.env` for local development:

```bash
MCP_TOKEN=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
# MCP_ALLOWED_HOSTS is optional locally — FastMCP allows localhost by default
```

Production (Heroku):

```bash
heroku config:set MCP_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" -a lamonkey-portfolio
heroku config:set MCP_ALLOWED_HOSTS="lamonkey-portfolio.herokuapp.com,jchen42.com" -a lamonkey-portfolio
```

## Authentication modes

The server runs in one of two modes depending on whether `MCP_OAUTH_ISSUER_URL` is set:

### Legacy mode (default — `MCP_OAUTH_ISSUER_URL` unset)

Routes mounted: `/mcp` only. `BearerAuthMiddleware` enforces `Authorization: Bearer <MCP_TOKEN>`.

This is the simplest mode and is what the curl examples below assume.

### OAuth mode (`MCP_OAUTH_ISSUER_URL` set)

Routes mounted by FastMCP:

- `/mcp` — same JSON-RPC endpoint, now validated against OAuth-issued access tokens by the SDK's own token middleware.
- `/authorize` — OAuth authorization endpoint. Wrapped in [`DjangoAdminGateMiddleware`](../src/mcp_oauth/middleware.py) so only a logged-in Django **superuser** can complete the grant. Anyone else is 302'd to `/admin/login/?next=…`.
- `/token` — OAuth token endpoint. Exchanges an authorization code + PKCE verifier + client_secret for an access token.
- `/.well-known/oauth-authorization-server` — RFC 8414 authorization server metadata.
- `/.well-known/oauth-protected-resource` — RFC 9728 protected resource metadata.

The legacy `MCP_TOKEN` keeps working — `DjangoOAuthProvider.load_access_token` falls back to comparing the incoming bearer against `os.getenv("MCP_TOKEN")`, returning a synthetic non-expiring `AccessToken`. This is deliberate: it lets curl scripts, the MCP Inspector, and the `/admin/` smoke tests keep working unchanged during the OAuth rollout.

#### Registering an OAuth client

OAuth client credentials are issued by a management command (no DCR):

```bash
heroku run -a lamonkey-portfolio "python src/manage.py register_oauth_client \
  --name 'Claude.ai' \
  --redirect-uri 'https://claude.ai/api/mcp/auth/callback'"
```

It prints `client_id` and `client_secret` once; both go into the connector form in claude.ai's Settings → Connectors → Add custom connector. The plaintext secret is stored in the `mcp_oauth_oauthclient` table (same threat model as `MCP_TOKEN` in Heroku config).

#### How the OAuth dance plays out

1. claude.ai redirects the operator's browser to `https://.../authorize?…`.
2. `DjangoAdminGateMiddleware` reads the Django `sessionid` cookie; if it doesn't resolve to an `is_superuser` user, it 302's to `/admin/login/?next=/authorize?…`.
3. Operator logs in to Django admin with their existing superuser credentials.
4. Browser bounces back to `/authorize?…`. This time the session cookie is present; the middleware passes through.
5. `DjangoOAuthProvider.authorize` mints a single-use authorization code, stores it in `OAuthAuthCode`, and returns the URL `https://claude.ai/api/mcp/auth/callback?code=<code>&state=<state>`. SDK redirects the browser there.
6. claude.ai's backend POSTs to `/token` with `grant_type=authorization_code`, the code, the client credentials, and the PKCE `code_verifier`. SDK verifies the secret + PKCE, calls `exchange_authorization_code`, returns `{"access_token": "...", "token_type": "Bearer", "expires_in": 604800}`.
7. claude.ai stores the access token. Every subsequent `/mcp` request is `Authorization: Bearer <access_token>`; the SDK validates it via `load_access_token`, which looks it up in `OAuthAccessToken`.

Tokens default to a 7-day TTL. There are no refresh tokens in v1; claude.ai re-runs the dance when the token expires.

#### Known limitations (v1)

- **Auto-approve consent** — the admin gate ensures only the operator can reach `/authorize`, but once they have, the SDK's auto-issued code is returned with no per-grant "Approve [client_name]?" prompt. Acceptable here because there's a single operator and clients are pre-registered. Adding an HTML consent step would be a follow-up.
- **No refresh tokens** — clients re-run the full dance every 7 days. Adding refresh is a small extension of the provider.
- **No Dynamic Client Registration** — clients must be added via `register_oauth_client`. The endpoint isn't even mounted.

### Why `MCP_ALLOWED_HOSTS` is needed

FastMCP's `streamable_http_app()` ships with DNS rebinding protection turned on. When `transport_security=None` (the convenient default), it auto-populates the allowlist with `["127.0.0.1:*", "localhost:*", "[::1]:*"]` — perfect for local dev, but it rejects every other Host header with 421. The server code in [`mcp_server/server.py`](../src/mcp_server/server.py) extends that allowlist with whatever you put in `MCP_ALLOWED_HOSTS`.

## Local testing

The MCP route is only mounted when the app runs through ASGI (uvicorn), not through `manage.py runserver`. Start it the way the Procfile does:

```bash
export MCP_TOKEN=dev-token-change-me
.venv/bin/python -m uvicorn --app-dir src Portfolio.asgi:application --host 127.0.0.1 --port 8000
```

### Smoke test with curl

The streamable-HTTP transport speaks JSON-RPC 2.0. A minimal `tools/list` round-trip:

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Calling `list_projects`:

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp \
  -H "Authorization: Bearer $MCP_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_projects","arguments":{}}}'
```

In practice, most flows go through the [MCP Inspector](https://github.com/modelcontextprotocol/inspector) or a client like Claude Desktop rather than raw curl — those handle the `initialize` handshake and capability negotiation for you.

### Inspector

```bash
npx @modelcontextprotocol/inspector
```

In the UI, choose the **Streamable HTTP** transport, point it at `http://127.0.0.1:8000/mcp`, and add the `Authorization: Bearer ...` header. You should see `list_projects` and `get_project` show up in the tool list.

### Claude Desktop / Claude Code

Add an entry to your client's MCP config (`~/Library/Application Support/Claude/claude_desktop_config.json` for Claude Desktop):

```json
{
  "mcpServers": {
    "portfolio": {
      "url": "https://lamonkey-portfolio.herokuapp.com/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN_HERE"
      }
    }
  }
}
```

Restart the client. The two tools should appear under the `portfolio` server.

## Files

| File | Purpose |
|---|---|
| [`src/mcp_server/server.py`](../src/mcp_server/server.py) | FastMCP app + tool definitions. |
| [`src/mcp_server/auth.py`](../src/mcp_server/auth.py) | Bearer-token ASGI middleware. |
| [`src/mcp_server/__init__.py`](../src/mcp_server/__init__.py) | Empty — marks the package. |
| [`src/Portfolio/asgi.py`](../src/Portfolio/asgi.py) | Composes Django + MCP under one Starlette router. |
| [`Procfile`](../Procfile) | Uses uvicorn so the ASGI composition is actually served. |

## Extending the server

To add a new tool, add another `@mcp.tool()`-decorated `async def` in `server.py`. The function's name becomes the tool name, its docstring becomes the tool description shown to the LLM, and its type annotations are turned into the JSON Schema for arguments and return value. Keep ORM access inside a synchronous helper wrapped in `sync_to_async` so the event loop stays unblocked.

For resources or prompts (the other MCP primitives), use `@mcp.resource()` and `@mcp.prompt()` from FastMCP respectively — currently neither is used by the portfolio server.
