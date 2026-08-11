# Deploying to Fly.io

The runbook for running this Django + MCP portfolio on Fly.io. It replaces the
Heroku deployment documented in [`HEROKU_LOGS.md`](./HEROKU_LOGS.md).

| Fact | Value |
|---|---|
| Fly app name | `lamonkey-portfolio` (set in [`fly.toml`](../fly.toml)) |
| Region | `iad` — change `primary_region` if you'd rather be elsewhere |
| Process | one machine running uvicorn against `Portfolio.asgi:application` |
| Migrations | `[deploy] release_command` in `fly.toml`, the analogue of Heroku's `release:` process |
| Database | Fly Managed Postgres |
| Media (images) | stays on S3 — nothing to migrate |

## Why this app can't be hosted statically

It is not just a database with images. `src/Portfolio/asgi.py` composes Django
with a Starlette app that serves `/mcp` (streamable-HTTP JSON-RPC) plus the
OAuth routes, and Django admin is the CMS for every model. That needs a
long-running ASGI process, a Postgres database, and object storage.

**The entrypoint must be ASGI.** `Portfolio.wsgi:application` boots fine but
serves *only* Django — `/mcp` and every OAuth route 404. The `Dockerfile` and
`docker-compose.yml` used to run gunicorn against `wsgi`; both now run uvicorn
against `asgi`.

## One-time setup

Everything below runs from the repo root, with flyctl already authenticated
(`fly auth whoami`).

### 1. Create the app

`fly.toml` is already committed, so skip `fly launch`'s scaffolding:

```bash
fly apps create lamonkey-portfolio
```

If you pick a different name, update `app` in `fly.toml` to match.

### 2. Create the database and attach it

```bash
fly mpg create --name portfolio-db --region iad
fly mpg attach <cluster-id> --app lamonkey-portfolio
```

`attach` sets the `DATABASE_URL` secret on the app, which is exactly what
`settings.py` reads via `dj_database_url`.

### 3. Set the remaining secrets

Everything the app needs that isn't in `fly.toml`'s `[env]`. Reuse the values
from Heroku — `heroku config -a lamonkey-portfolio` prints them.

```bash
fly secrets set \
  SECRET_KEY='<existing django secret key>' \
  ALLOWED_HOSTS='jchen42.com,www.jchen42.com,lamonkey-portfolio.fly.dev' \
  CSRF_TRUSTED_ORIGINS='https://jchen42.com,https://www.jchen42.com,https://lamonkey-portfolio.fly.dev' \
  AWS_STORAGE_BUCKET_NAME='<bucket>' \
  AWS_ACCESS_KEY_ID='<key id>' \
  AWS_SECRET_ACCESS_KEY='<secret>' \
  MCP_OAUTH_ISSUER_URL='https://jchen42.com' \
  MCP_ALLOWED_HOSTS='jchen42.com,www.jchen42.com,lamonkey-portfolio.fly.dev' \
  MCP_ALLOWED_ORIGINS='https://jchen42.com,https://www.jchen42.com' \
  --app lamonkey-portfolio
```

Notes on the MCP variables — these are the ones that bite after a host change:

- `MCP_ALLOWED_HOSTS` / `MCP_ALLOWED_ORIGINS` feed FastMCP's DNS-rebinding
  protection. If the new hostname isn't listed, **every `/mcp` request returns
  421 "Invalid Host header"** while the rest of the site looks perfectly fine.
- `MCP_OAUTH_ISSUER_URL` switches the app from legacy `MCP_TOKEN` bearer auth to
  full OAuth. Set one or the other; if neither is set, `/mcp` answers 503 with
  "MCP_TOKEN is not configured".
- Registered OAuth clients live in the database, so they survive the move as
  long as you restore the dump in step 4. Their redirect URIs do *not* get
  rewritten — re-register any client whose callback pointed at the old host.

### 4. Move the data over

Media is on S3 and stays there. Only Postgres moves:

```bash
heroku pg:backups:capture -a lamonkey-portfolio
heroku pg:backups:download -a lamonkey-portfolio   # -> latest.dump

fly mpg connect <cluster-id>   # grab the connection string it prints
pg_restore --no-owner --no-acl --clean --if-exists \
  -d '<fly postgres connection string>' latest.dump
```

Restore *before* the first deploy so `release_command`'s `migrate` finds the
schema already at the right version and becomes a no-op.

### 5. Deploy

```bash
fly deploy
```

This builds the `Dockerfile`, runs `migrate` in a throwaway release machine,
then shifts traffic. Verify:

```bash
fly logs -a lamonkey-portfolio
curl -sI https://lamonkey-portfolio.fly.dev/ | head -1
curl -s -o /dev/null -w '%{http_code}\n' https://lamonkey-portfolio.fly.dev/.well-known/oauth-protected-resource
```

Expect `200` from both. A `421` on MCP routes means `MCP_ALLOWED_HOSTS` is
missing the hostname you just called.

### 6. Cut the domain over

```bash
fly certs add jchen42.com --app lamonkey-portfolio
fly certs add www.jchen42.com --app lamonkey-portfolio
```

`fly certs show jchen42.com` prints the A/AAAA (or CNAME) records to set at
your DNS provider. Certificates issue once DNS resolves. Only then remove the
domain from Heroku — doing it in the other order takes the site down while
certs issue.

### 7. Decommission Heroku

Once the Fly deploy has served the real domain for a day or two:

```bash
heroku apps:destroy -a lamonkey-portfolio --confirm lamonkey-portfolio
```

Keep `latest.dump` somewhere safe first. This is irreversible.

## Day-to-day operations

Heroku equivalents, for muscle memory:

| Task | Heroku | Fly |
|---|---|---|
| Tail logs | `heroku logs -t` | `fly logs` |
| Shell | `heroku run bash` | `fly ssh console` |
| Django shell | `heroku run python src/manage.py shell` | `fly ssh console -C "python manage.py shell"` |
| One-off migrate | `heroku run ... migrate` | `fly ssh console -C "python manage.py migrate"` |
| Read config | `heroku config` | `fly secrets list` (names only — values are write-only) |
| Set config | `heroku config:set K=V` | `fly secrets set K=V` |
| Restart | `heroku restart` | `fly apps restart lamonkey-portfolio` |
| Scale | `heroku ps:scale web=1` | `fly scale count 1` |

Note the working directory differs: the image copies `src/` to `/app`, so it's
`python manage.py …` inside the container, not `python src/manage.py …`.

Creating the admin user on a fresh database:

```bash
fly ssh console -C "python manage.py createsuperuser"
```

## Scale to zero

`fly.toml` sets `auto_stop_machines = "stop"` with `min_machines_running = 0`,
so the machine shuts down when idle and Fly stops billing compute for it. The
cost is a cold start of a few seconds on the first request after a quiet spell
— including the first `/mcp` call, which an impatient MCP client may read as a
timeout. If that gets annoying:

```toml
min_machines_running = 1
```

## Static files

WhiteNoise serves `STATIC_ROOT`, and `collectstatic` runs at **image build
time** in the `Dockerfile`. Heroku's Python buildpack did this implicitly; a
container won't, and skipping it leaves Django admin unstyled. `settings.py`
reads `SECRET_KEY` and `DATABASE_URL` at import time, so the build passes
throwaway values for that one command — they never serve traffic.
