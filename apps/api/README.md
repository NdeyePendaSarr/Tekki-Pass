# Tekki-Pass API

FastAPI service (Python 3.12, fully typed). See the [root README](../../README.md) for the big picture.

```bash
uv sync                                   # install dependencies (pinned in uv.lock)
uv run uvicorn app.main:app --reload      # http://localhost:8000/health
uv run pytest                             # tests
uv run ruff check . && uv run ruff format --check . && uv run mypy
```
