from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.schemas.health import HealthResponse
from app.schemas.search import EnvelopeResponse
from app.utils.logger import logger

router = APIRouter()

@router.get("/health", response_model=EnvelopeResponse[HealthResponse])
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check API and database connection status.
    """
    db_status = "healthy"
    try:
        # Verify db connectivity by executing a lightweight query
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database connectivity check failed: {str(e)}")
        db_status = "unhealthy"

    return EnvelopeResponse(
        success=True,
        data=HealthResponse(
            status="healthy",
            database=db_status
        )
    )
