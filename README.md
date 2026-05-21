## Portfolio

A static portfolio site implemented with Django.

### Local development

- Install Python 3.9+ and pip
- Create virtualenv and install requirements: `pip install -r requirements.txt`
- Create a `.env` file (see example below)
- Run: `python src/manage.py runserver`

### Deployment

Deploy on a platform like Render/Heroku/AWS. Ensure environment variables are set before starting the app.

#### Configuration (Environment variables)

- **SECRET_KEY**: Django secret key. Required in production.
- **MODE**: `development` enables `DEBUG`; any other value disables it. Default: production (DEBUG off). When `MODE=development`, `ALLOWED_HOSTS` is augmented with `localhost` and `127.0.0.1`.
- **ALLOWED_HOSTS**: Comma-separated hosts (e.g., `example.com,www.example.com`).
- **CSRF_TRUSTED_ORIGINS**: Comma-separated origins (e.g., `https://example.com,https://www.example.com`).
- **DATABASE_URL**: Database URL (e.g., `postgres://user:pass@host:5432/dbname`). Required.
- **AWS_STORAGE_BUCKET_NAME**: S3 bucket for media (optional).
- **AWS_ACCESS_KEY_ID**: AWS access key (optional).
- **AWS_SECRET_ACCESS_KEY**: AWS secret key (optional).

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
