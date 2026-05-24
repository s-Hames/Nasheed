from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.utils.logger import logger

class NasheedException(Exception):
    """Base exception for all Nasheed application errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

class VideoNotFoundException(NasheedException):
    def __init__(self, message: str = "Video not found", details: dict | None = None):
        super().__init__(
            message=message,
            code="VIDEO_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details
        )

class StreamExtractionException(NasheedException):
    def __init__(self, message: str = "Failed to extract playable audio stream", details: dict | None = None):
        super().__init__(
            message=message,
            code="STREAM_EXTRACTION_FAILED",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )

class SearchException(NasheedException):
    def __init__(self, message: str = "YouTube search query failed", details: dict | None = None):
        super().__init__(
            message=message,
            code="SEARCH_FAILED",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )

class RateLimitException(NasheedException):
    def __init__(self, message: str = "Too many requests. Please try again later.", details: dict | None = None):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )

async def nasheed_exception_handler(request: Request, exc: NasheedException) -> JSONResponse:
    logger.warning(f"Application error: {exc.code} - {exc.message} (Status: {exc.status_code})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("An unhandled exception occurred")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again.",
                "details": {}
            }
        }
    )

def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(NasheedException, nasheed_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
