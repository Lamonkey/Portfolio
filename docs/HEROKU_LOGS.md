# Checking Heroku Logs & Debugging the Deployment

> **Superseded.** The app is moving to Fly.io — see
> [`DEPLOY_FLY.md`](./DEPLOY_FLY.md). Keep this around until the Heroku app is
> destroyed; the `heroku config` / `pg:backups` commands here are what you use
> to pull the secrets and the database dump across.

A reusable runbook for inspecting the live deployment on Heroku — for both
humans and agents. The app is the Django + MCP portfolio at
`https://lamonkey-portfolio.herokuapp.com` (custom domain `jchen42.com`).

| Fact | Value |
|---|---|
| Heroku app name | `lamonkey-portfolio` |
| Web URL | `https://lamonkey-portfolio.herokuapp.com/` |
| Git remote | `heroku` → `https://git.heroku.com/lamonkey-portfolio.git` |
| Process types | `web` (uvicorn ASGI) + `release` (runs migrations) — see [`Procfile`](../Procfile) |
| Owner | `88therisingsun@gmail.com` |

All `heroku` commands below take `-a lamonkey-portfolio` to target the app
explicitly. You can drop it if the `heroku` git remote is set (it is in this
repo), but being explicit is safer in scripts and for agents.

## Prerequisites

```bash
heroku --version          # CLI installed? (brew install heroku/brew/heroku)
heroku auth:whoami        # logged in? otherwise: heroku login
```

If `heroku auth:whoami` fails, the rest of this doc won't work until you
`heroku login` (opens a browser). In a headless/agent context, set
`HEROKU_API_KEY` to a token from `heroku authorizations:create`.

## 1. Tail / read the logs

```bash
# Last 200 lines (most useful default)
heroku logs -n 200 -a lamonkey-portfolio

# Live tail — follow new lines as they arrive (Ctrl-C to stop)
heroku logs --tail -a lamonkey-portfolio

# Only application output (your Django/uvicorn logs), skip router/system noise
heroku logs -n 200 --source app -a lamonkey-portfolio

# Only the HTTP router (status codes, latency, paths)
heroku logs -n 200 --source heroku --dyno router -a lamonkey-portfolio

# Only the web dyno
heroku logs -n 200 --dyno web -a lamonkey-portfolio
```

### Reading a router line

```
heroku[router]: at=info method=GET path="/mcp" host=lamonkey-portfolio.herokuapp.com
  request_id=... fwd="172.58.254.237" dyno=web.1 connect=0ms service=1ms
  status=401 bytes=74 protocol=http1.1
```

- `status=` — the HTTP code returned. `5xx`/`H1x` codes are real problems.
- `service=` — how long the dyno took. Spikes mean slow handlers.
- `path=` / `method=` — what was requested.
- `host=` — `jchen42.com` vs `herokuapp.com` tells you which domain was hit.

> **Noise warning:** this app is public and constantly scraped by bots probing
> for `/.env`, `/wp-content/...`, `/vercel.json`, etc. Those produce a flood of
> `404` lines from random IPs — they are **not** bugs. Filter to your own
> traffic with `grep`, e.g. `heroku logs -n 500 -a lamonkey-portfolio | grep -v "404"`
> or grep for the specific path you care about (`grep "/mcp"`).

## 2. Check app & dyno health

```bash
heroku apps:info -a lamonkey-portfolio     # stack, dynos, addons, slug size
heroku ps -a lamonkey-portfolio            # are dynos up? crashed? restarting?
heroku releases -a lamonkey-portfolio      # deploy history (v123, who, when)
heroku releases:info v123 -a lamonkey-portfolio   # detail on one release
```

A crashed web dyno shows as `crashed` in `heroku ps` and emits `H10 App crashed`
router errors. The crash reason is in the **app** logs around the dyno's last
restart — `heroku logs -n 200 --source app -a lamonkey-portfolio`.

## 3. Inspect config (env vars)

```bash
heroku config -a lamonkey-portfolio                 # all vars
heroku config:get MCP_OAUTH_ISSUER_URL -a lamonkey-portfolio   # one var
heroku config -a lamonkey-portfolio | grep -iE "MCP|OAUTH"     # filter
```

> Config values are **secrets** (DB URL, AWS keys, `SECRET_KEY`, `MCP_TOKEN`).
> Don't paste full `heroku config` output into shared channels or commit it.

Set / unset:

```bash
heroku config:set MCP_ALLOWED_HOSTS="lamonkey-portfolio.herokuapp.com,jchen42.com" -a lamonkey-portfolio
heroku config:unset SOME_VAR -a lamonkey-portfolio
```

Changing config triggers a new release (dyno restart).

## 4. Run one-off commands / a shell on the dyno

```bash
# Django shell against the production DB
heroku run "python src/manage.py shell" -a lamonkey-portfolio

# Check migration state
heroku run "python src/manage.py showmigrations" -a lamonkey-portfolio

# A throwaway bash shell on a fresh dyno
heroku run bash -a lamonkey-portfolio
```

The `release:` phase in the [`Procfile`](../Procfile) already runs
`python src/manage.py migrate --noinput` on every deploy, so migrations should
be applied automatically — `showmigrations` is how you confirm it.

## 5. Probe HTTP endpoints directly

Often faster than reading logs — hit the endpoint and read the response:

```bash
# Status code only
curl -s -o /dev/null -w "%{http_code}\n" https://lamonkey-portfolio.herokuapp.com/

# Full headers (great for auth challenges / redirects)
curl -s -i https://lamonkey-portfolio.herokuapp.com/mcp | head -20
```

A `421 Invalid Host header` from `/mcp` means `MCP_ALLOWED_HOSTS` is missing the
host you're using (see [MCP_SERVER.md](MCP_SERVER.md)).

## Worked example: "the /mcp endpoint returns 401"

This is the canonical investigation this runbook was written for.

1. **Reproduce:** `curl -s -i https://lamonkey-portfolio.herokuapp.com/mcp`
   → `401 Unauthorized` with header
   `WWW-Authenticate: Bearer error="invalid_token", error_description="Authentication required", resource_metadata=".../.well-known/oauth-protected-resource"`.
2. **Interpret:** that header is an **OAuth challenge**, not a crash. The MCP
   server is up and deliberately refusing unauthenticated requests. A plain
   browser GET will always show this — browsers don't perform the MCP/OAuth
   handshake.
3. **Confirm the server is healthy** by checking the logs show a clean `401`
   (not a `5xx` or `H10`): `heroku logs -n 50 -a lamonkey-portfolio | grep "/mcp"`.
4. **Confirm the OAuth discovery chain** is intact:
   ```bash
   curl -s https://lamonkey-portfolio.herokuapp.com/.well-known/oauth-protected-resource
   curl -s https://lamonkey-portfolio.herokuapp.com/.well-known/oauth-authorization-server
   ```
   Both should return `200` with JSON.
5. **Confirm the endpoint actually works** with a valid token:
   ```bash
   TOKEN=$(heroku config:get MCP_TOKEN -a lamonkey-portfolio)
   curl -s -i -X POST https://lamonkey-portfolio.herokuapp.com/mcp \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
   ```
   A `200` with an `event: message` / `serverInfo` body means the server is
   fully functional and the 401 was just the auth gate doing its job.

**Conclusion of that investigation:** nothing is broken in the deploy. Since the
OAuth rollout (commit `f1fd042`), `/mcp` requires authentication. "It worked
before" because the older flow used a static `MCP_TOKEN` bearer, and/or the
client relied on **Dynamic Client Registration**, which this server has
**disabled** (`/register` → 404). See
[MCP_SERVER.md → Authentication modes](MCP_SERVER.md#authentication-modes) for
how to connect under each mode.

## Common signals cheat-sheet

| Symptom | Likely cause | Where to look |
|---|---|---|
| `401` on `/mcp` with `WWW-Authenticate: Bearer` | Expected OAuth challenge — not a bug | [MCP_SERVER.md](MCP_SERVER.md) |
| `421 Invalid Host header` | `MCP_ALLOWED_HOSTS` missing the host | `heroku config` |
| `H10 App crashed` | App failed to boot | `heroku logs --source app`, `heroku ps` |
| `H14 No web dynos running` | Dyno scaled to 0 | `heroku ps:scale web=1 -a lamonkey-portfolio` |
| `503 MCP_TOKEN is not configured` | `MCP_TOKEN` unset (legacy mode) | `heroku config:get MCP_TOKEN` |
| Flood of `404`s for `/.env`, `/wp-*` | Bot scanners — ignore | filter with `grep` |
| Migrations not applied | `release` phase failed | `heroku releases`, release-phase logs |

## See also

- [MCP_SERVER.md](MCP_SERVER.md) — full MCP server + OAuth architecture and how to connect clients.
- [Heroku CLI logging docs](https://devcenter.heroku.com/articles/logging)
- [Heroku error codes (H10, H12, R14, …)](https://devcenter.heroku.com/articles/error-codes)
