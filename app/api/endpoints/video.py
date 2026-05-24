from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.video import Video
from app.models.trusted_channel import TrustedChannel
from app.schemas.video import VideoResponse
from app.schemas.search import EnvelopeResponse
from app.services.scoring import calculate_score, is_valid_nasheed
from app.services.youtube_search import fetch_video_metadata_async
from app.core.exceptions import NasheedException

router = APIRouter()

@router.get("/video/{video_id}", response_model=EnvelopeResponse[VideoResponse])
async def get_video_details(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve details for a specific YouTube video.
    If the video is not present in the local database, fetch metadata from YouTube,
    verify against scoring filter, and catalog it.
    """
    if not video_id or len(video_id) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube video ID format. Must be 11 characters."
        )

    # 1. Lookup video in database
    stmt = select(Video).where(Video.youtube_id == video_id)
    res = await db.execute(stmt)
    video = res.scalar_one_or_none()

    if not video:
        # Resolve from YouTube directly
        metadata = await fetch_video_metadata_async(video_id)
        
        # Load trusted channels
        trusted_stmt = select(TrustedChannel.channel_name)
        trusted_res = await db.execute(trusted_stmt)
        trusted_channels = [row[0] for row in trusted_res.all()]
        
        score = calculate_score(metadata['title'], metadata['channel'], trusted_channels)
        if not is_valid_nasheed(score):
            raise NasheedException(
                message="Requested video does not pass suitability score for nasheeds.",
                code="FILTERED_CONTENT",
                status_code=status.HTTP_400_BAD_REQUEST,
                details={"title": metadata['title'], "score": score}
            )
            
        # Insert new video into DB (play_count starts at 0 since it hasn't been played yet)
        video = Video(
            youtube_id=video_id,
            title=metadata['title'],
            thumbnail=metadata['thumbnail'],
            duration=metadata['duration'],
            channel=metadata['channel'],
            score=score,
            upload_date=metadata['upload_date'],
            play_count=0
        )
        db.add(video)
        try:
            await db.commit()
            await db.refresh(video)
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to catalog video details in database: {str(e)}"
            )

    return EnvelopeResponse(
        success=True,
        data=VideoResponse.model_validate(video)
    )
