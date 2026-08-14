"""Security response headers for the loopback API (AXW-RUN-206).

The backend only ever talks to the Tauri shell on 127.0.0.1, but browser
best practice still applies: no framing, no MIME sniffing, no referrer
leakage, and a baseline Permissions-Policy. The page-level CSP for the
workspace UI itself is set by the UI layer once it moves into frontendDist
(task pack §9.3); these headers cover every API response today.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Awaitable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "screen-wake-lock=(), window-management=()"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds baseline security headers to every loopback API response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        return response
