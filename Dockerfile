FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies. psycopg2-binary ships prebuilt wheels, so no
# compiler or libpq headers are needed at build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY src/ /app/

# Collect static files into STATIC_ROOT so WhiteNoise has something to serve.
# On Heroku the Python buildpack did this for us; in a container we do it here,
# at build time, so the image is self-contained. settings.py reads these two at
# import time, so give it throwaway values — they never serve traffic.
RUN SECRET_KEY=build-only DATABASE_URL=sqlite:///build.sqlite3 \
    python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run the ASGI app. This MUST be asgi (not wsgi): the /mcp endpoint and the
# OAuth routes are mounted in Portfolio/asgi.py and do not exist under WSGI.
CMD ["sh", "-c", "python -m uvicorn Portfolio.asgi:application --host 0.0.0.0 --port ${PORT:-8000}"]
