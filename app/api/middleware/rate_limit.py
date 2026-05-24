import time
from collections import defaultdict
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.utils.logger import logger

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Lightweight, in-memory sliding-window rate limiting middleware.
    Filters requests by client IP.
    """
    def __init__(self, app, requests_limit: int = None):
        super().__init__(app)
        self.limit = requests_limit or settings.RATE_LIMIT_PER_MINUTE
        # In-memory store: client_ip -> list of epoch timestamps
        self.request_timestamps = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Bypass rate limiter for health check endpoints
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean up timestamps older than 60 seconds
        self.request_timestamps[client_ip] = [
            t for t in self.request_timestamps[client_ip] if now - t < 60
        ]

        # Check if limit is exceeded
        if len(self.request_timestamps[client_ip]) >= self.limit:
            logger.warning(f"Rate limit exceeded for client IP: {client_ip} (Limit: {self.limit}/min)")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "details": {
                            "client_ip": client_ip,
                            "limit_per_minute": self.limit
                        }
                    }
                }
            )

        # Record the current request timestamp
        self.request_timestamps[client_ip].append(now)
        
        return await call_next(request)
