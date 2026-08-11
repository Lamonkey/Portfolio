## Portfolio

A static portfolio site implemented with Django.

### Local development

- Install Python 3.9+ and pip
- Create virtualenv and install requirements: `pip install -r requirements.txt`
- Create a `.env` file (see example below)
- Run: `python src/manage.py runserver`

### Deployment

Deployed on Fly.io — see [`docs/DEPLOY_FLY.md`](docs/DEPLOY_FLY.md) for the full
runbook (app creation, Postgres, secrets, domain cutover, day-to-day commands).
Configuration lives in [`fly.toml`](fly.toml); the image is built from the
[`Dockerfile`](Dockerfile).

The entrypoint must be **ASGI** (`Portfolio.asgi:application`). Under WSGI the
site renders fine but `/mcp` and the OAuth routes don't exist at all, since
they're mounted in `src/Portfolio/asgi.py`.

Ensure environment variables are set before starting the app.

#### Configuration (Environment variables)

-**SECRET_KEY**: Django secret key. Required in production.

-**MODE**: `development` enables `DEBUG`; any other value disables it. Default: production (DEBUG off).
 -**MODE**: `development` enables `DEBUG`; any other value disables it. Default: production (DEBUG off). When `MODE=development`, `ALLOWED_HOSTS` becomes whatever you set plus `localhost` and `127.0.0.1`.

-**ALLOWED_HOSTS**: Comma-separated hosts (e.g., `example.com,www.example.com`).
 -**ALLOWED_HOSTS**: Comma-separated hosts (e.g., `example.com,www.example.com`). In development, the list is augmented with `localhost` and `127.0.0.1`.

-**CSRF_TRUSTED_ORIGINS**: Comma-separated origins (e.g., `https://example.com,https://www.example.com`).

-**DATABASE_URL**: Database URL (e.g., `postgres://user:pass@host:5432/dbname`). Required.

-**AWS_STORAGE_BUCKET_NAME**: S3 bucket for media (optional).

-**AWS_ACCESS_KEY_ID**: AWS access key (optional).

-**AWS_SECRET_ACCESS_KEY**: AWS secret key (optional).

MCP-related (see [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md)):

-**MCP_OAUTH_ISSUER_URL**: Public base URL of the app, e.g. `https://example.com`. Setting it enables the OAuth routes; leaving it unset falls back to `MCP_TOKEN` bearer auth.

-**MCP_TOKEN**: Legacy bearer token for `/mcp`. Only used when `MCP_OAUTH_ISSUER_URL` is unset. If neither is set, `/mcp` returns 503.

-**MCP_ALLOWED_HOSTS**: Comma-separated Host header values accepted by the MCP endpoint. **Must include your public hostname after a host or platform change**, or every `/mcp` request returns 421.

-**MCP_ALLOWED_ORIGINS**: Comma-separated Origin header values for browser-based MCP clients.

Example `.env`:

```bash
SECRET_KEY=change-me
MODE=development
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
# Optional: S3-backed media storage
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret
```

### Docker

Quick start with Postgres and the web app:

```bash
docker compose up --build
```

This will:
- Start Postgres (service `db`)
- Build and run the Django app (service `web`)
- Run migrations and `collectstatic` automatically

Default ports:
- Web: `http://localhost:8000`
- Postgres: internal only, accessible from `web` as `db:5432`

Environment variables used by the container (see above Configuration):
- `DATABASE_URL=postgres://postgres:postgres@db:5432/portfolio`
- Provide your own `SECRET_KEY` for non-dev usage

# Protfolio

A Portfolio

This is a static website used to present my projects. Implemented using Django.

### Environment variables

Set these in your shell or a `.env` file (loaded via `python-dotenv`).

-**SECRET_KEY**: Django secret key. Required in production.

-**MODE**: Set to `development` to enable `DEBUG`; any other value disables it. Default: production (DEBUG off).

-**ALLOWED_HOSTS**: Comma-separated hostnames allowed to serve the app (e.g., `example.com,www.example.com`).

-**CSRF_TRUSTED_ORIGINS**: Comma-separated trusted origins for CSRF (e.g., `https://example.com,https://www.example.com`).

-**DATABASE_URL**: Database connection URL (e.g., `postgres://user:pass@host:5432/dbname`). Required.

-**AWS_STORAGE_BUCKET_NAME**: S3 bucket name for media storage (if using S3).

-**AWS_ACCESS_KEY_ID**: AWS access key (if using S3).

-**AWS_SECRET_ACCESS_KEY**: AWS secret key (if using S3).

Example `.env`:

```bash

SECRET_KEY=change-me

MODE=development

ALLOWED_HOSTS=localhost,127.0.0.1

CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1

DATABASE_URL=sqlite:///db.sqlite3

# For S3-backed media storage (optional)

AWS_STORAGE_BUCKET_NAME=your-bucket

AWS_ACCESS_KEY_ID=your-access-key-id

AWS_SECRET_ACCESS_KEY=your-secret

```
