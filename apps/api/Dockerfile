# syntax=docker/dockerfile:1
# Multi-stage build: resolve pinned dependencies with uv, then copy the venv into a slim runtime.

FROM python:3.12-slim-trixie AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
# --frozen: fail instead of silently changing the lockfile.
RUN uv sync --frozen --no-dev

FROM python:3.12-slim-trixie AS runtime
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=build /app/.venv /app/.venv
COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
# Apply database migrations, then start the server (exec: uvicorn receives stop signals).
# No uvicorn access log: it prints raw paths (request tokens) and client IPs. The API
# writes its own request log instead (app/observability.py).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
