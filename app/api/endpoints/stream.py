from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.video import Video
from app.models.trusted_channel import TrustedChannel
from app.schemas.search import EnvelopeResponse, StreamResponse
from app.services.stream_extractor import extract_stream_async
from app.services.scoring import calculate_score, is_valid_nasheed
from app.services.youtube_search import fetch_video_metadata_async
from app.core.exceptions import NasheedException

router = APIRouter()

@router.get("/stream/{video_id}", response_model=EnvelopeResponse[StreamResponse])
async def get_audio_stream(
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Extract direct audio streaming URL.
    Increments play_count of the video in the database.
    """
    if not video_id or len(video_id) != 11:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube video ID format. Must be 11 characters."
        )

    # 1. Look up the video in database to verify it exists and is cataloged
    stmt = select(Video).where(Video.youtube_id == video_id)
    res = await db.execute(stmt)
    video = res.scalar_one_or_none()

    if video:
        # Increment play_count
        video.play_count += 1
        try:
            await db.commit()
        except Exception:
            await db.rollback()
    else:
        # If the video does not exist yet (direct stream call), pull its metadata to score it
        metadata = await fetch_video_metadata_async(video_id)
        
        # Load trusted channels for score calculation
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
            
        # Catalog the video in DB with play_count = 1
        video = Video(
            youtube_id=video_id,
            title=metadata['title'],
            thumbnail=metadata['thumbnail'],
            duration=metadata['duration'],
            channel=metadata['channel'],
            score=score,
            upload_date=metadata['upload_date'],
            play_count=1
        )
        db.add(video)
        try:
            await db.commit()
        except Exception:
            await db.rollback()

    # 2. Extract playable direct URL
    stream_url = await extract_stream_async(video_id)

    return EnvelopeResponse(
        success=True,
        data=StreamResponse(
            video_id=video_id,
            stream_url=stream_url
        )
    )
