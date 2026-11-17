"""Structured logs without personal data (threat model: "Personal data in logs").

One JSON line per request: request id, method, route *template*, status and duration.
Never logged: the raw path (it carries the request token), the query string, headers
(NIP-98 signatures, client IP), bodies (phone numbers), or the client address.
Uvicorn's own access log prints raw paths and IPs, so it is turned off (--no-access-log).
"""

import json
import logging
import re
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("app.http")

#: Request id of the request being handled, added to every log line written meanwhile.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

REQUEST_ID_HEADER = "X-Request-ID"
#: An incoming id is kept only if it looks like an id: no free text reaches the logs.
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")

#: Standard LogRecord attributes: everything else passed through `extra=` is a field.
_RECORD_ATTRIBUTES = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, easy to search with `docker compose logs | jq`."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id is not None:
            entry["request_id"] = request_id
        for key, value in vars(record).items():
            if key not in _RECORD_ATTRIBUTES:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """JSON logs for the API's own loggers (uvicorn only configures its own)."""
    app_logger = logging.getLogger("app")
    if not app_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        app_logger.addHandler(handler)
        app_logger.setLevel(logging.INFO)


def _route_template(scope: Scope) -> str:
    """The matched route as declared ("/attestation-requests/{token}"), never the raw path.

    The router stores the matched route in the scope; nothing matched: "unmatched".
    """
    path: object = getattr(scope.get("route"), "path", None)
    if isinstance(path, str):
        return path
    return "unmatched"


def _request_id(scope: Scope) -> str:
    for name, value in scope.get("headers", ()):
        if name == REQUEST_ID_HEADER.lower().encode():
            candidate = value.decode("latin-1")
            if _VALID_REQUEST_ID.fullmatch(candidate):
                return candidate
    return uuid.uuid4().hex


class RequestLogMiddleware:
    """Logs one line per HTTP request and returns its id in the X-Request-ID header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _request_id(scope)
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status = 500  # if the app fails before sending a response

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.lower().encode(), request_id.encode()))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "route": _route_template(scope),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)
