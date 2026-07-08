from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from collections.abc import Callable
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from .config import RateLimitConfig, SecurityConfig


class RequestSecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        security: SecurityConfig,
        rate_limit: RateLimitConfig,
    ) -> None:
        super().__init__(app)
        self.security = security
        self.rate_limit = rate_limit
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id

        auth_error = self._authenticate(request)
        if auth_error is not None:
            return self._with_headers(auth_error, request_id)

        rate_limit_error = self._rate_limit(request)
        if rate_limit_error is not None:
            return self._with_headers(rate_limit_error, request_id)

        response = await call_next(request)
        return self._with_headers(response, request_id)

    def _authenticate(self, request: Request) -> JSONResponse | None:
        if not self.security.api_key_enabled:
            return None
        if self._is_public_path(request.url.path):
            return None

        expected_key = os.getenv(self.security.api_key_env)
        provided_key = request.headers.get("x-api-key")
        if not expected_key or provided_key != expected_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "unauthorized",
                        "message": "A valid API key is required.",
                    }
                },
            )
        return None

    def _rate_limit(self, request: Request) -> JSONResponse | None:
        if not self.rate_limit.enabled:
            return None
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.requests[client]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= self.rate_limit.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please retry later.",
                    }
                },
            )
        window.append(now)
        return None

    def _is_public_path(self, path: str) -> bool:
        return any(
            path == public_path or path.startswith(f"{public_path}/")
            for public_path in self.security.public_paths
        )

    def _with_headers(self, response: Response, request_id: str) -> Response:
        response.headers["x-request-id"] = request_id
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["cache-control"] = "no-store"
        return response
