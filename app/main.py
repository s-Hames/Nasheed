from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
from sqlalchemy import select

from app.core.config import settings
from app.utils.logger import setup_logging, logger
from app.core.exceptions import register_exception_handlers
from app.database.session import engine, AsyncSessionLocal
from app.database.base import Base
from app.models.trusted_channel import TrustedChannel

# Import Routers
from app.api.endpoints.health import router as health_router
from app.api.endpoints.search import router as search_router
from app.api.endpoints.stream import router as stream_router
from app.api.endpoints.video import router as video_router

# Import Middleware
from app.api.middleware.rate_limit import RateLimitMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    App lifespan context manager handling startup initialization and shutdown cleanup.
    """
    # 1. Setup logging system
    setup_logging()
    logger.info("Initializing Nasheed Backend MVP...")

    # 2. Database migrations (create tables if they do not exist)
    logger.info("Synchronizing database tables...")
    async with engine.begin() as conn:
        # Import models inside to ensure they are registered on the Base metadata
        import app.models # noqa
        await conn.run_sync(Base.metadata.create_all)

    # 3. Seed default trusted channels if the table is empty
    async with AsyncSessionLocal() as session:
        try:
            stmt = select(TrustedChannel)
            res = await session.execute(stmt)
            if not res.scalars().first():
                logger.info("Seeding default trusted channels...")
                default_channels = [
                    "Muhammad Al Muqit",
                    "Labbayk",
                    "Ahmed Bukhatir",
                    "Mishary Rashid Alafasy",
                    "Zain Bhikha",
                    "Sami Yusuf",
                    "Maher Zain"
                ]
                for channel in default_channels:
                    session.add(TrustedChannel(channel_name=channel))
                await session.commit()
                logger.info("Seeding completed successfully.")
        except Exception as e:
            logger.error(f"Error seeding trusted channels during startup: {str(e)}")
            await session.rollback()

    yield

    # 4. Cleanup database connections on shutdown
    logger.info("Cleaning up database engine resources...")
    await engine.dispose()
    logger.info("Shutdown complete.")

# Initialize FastAPI App with Automatic OpenAPI docs enabled
app = FastAPI(
    title="Nasheed Search & Stream API",
    description="A backend-only MVP to search and extract playable audio streams for nasheeds safely.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration (Enable cross-origin calls for mobile and web frontends)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom sliding window IP-based rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    requests_limit=settings.RATE_LIMIT_PER_MINUTE
)

# Standardized app exception handlers
register_exception_handlers(app)

@app.get("/", response_class=HTMLResponse)
async def get_index():
    """
    Serve the single-page application dashboard on the root path.
    """
    from app.static.index_html import INDEX_HTML
    return HTMLResponse(content=INDEX_HTML, status_code=200)

# Mounting routes
app.include_router(health_router, tags=["Health"])
app.include_router(search_router, tags=["Search & Trending"])
app.include_router(stream_router, tags=["Streaming"])
app.include_router(video_router, tags=["Video Details"])
