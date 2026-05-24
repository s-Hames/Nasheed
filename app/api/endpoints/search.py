from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database.session import get_db
from app.models.video import Video
from app.models.search_history import SearchHistory
from app.models.trusted_channel import TrustedChannel
from app.schemas.video import VideoResponse
from app.schemas.search import EnvelopeResponse
from app.services.youtube_search import search_youtube_async
from app.services.scoring import calculate_score, is_valid_nasheed
from app.core.exceptions import SearchException
from app.core.config import settings
from app.utils.logger import logger

router = APIRouter()

@router.get("/search", response_model=EnvelopeResponse[List[VideoResponse]])
async def search_nasheeds(
    q: str = Query(..., min_length=1, description="The search query for nasheeds"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search YouTube for nasheeds, apply filtering/scoring rules,
    upsert matching videos into database, and return results.
    """
    clean_query = q.strip().lower()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )

    # 1. Update/Record search history
    try:
        history_stmt = select(SearchHistory).where(SearchHistory.query == clean_query)
        history_res = await db.execute(history_stmt)
        history = history_res.scalar_one_or_none()
        
        if history:
            history.hit_count += 1
        else:
            history = SearchHistory(query=clean_query, hit_count=1)
            db.add(history)
        await db.commit()
    except Exception as e:
        # Commit failures on search history should not block search results, just log it
        await db.rollback()
        logger.error(f"Failed to record search history: {str(e)}")

    # 2. Get trusted channels list
    trusted_stmt = select(TrustedChannel.channel_name)
    trusted_res = await db.execute(trusted_stmt)
    trusted_channels = [row[0] for row in trusted_res.all()]

    # 3. Query YouTube
    # Bias the query toward nasheeds for better results
    biased_query = q.strip()
    nasheed_terms = ["nasheed", "anasheed", "naat", "hamd", "ilahi", "qasida", "نشيد"]
    if not any(term in biased_query.lower() for term in nasheed_terms):
        biased_query = f"{biased_query} nasheed"

    # Overfetch 3x to have enough results after score filtering
    fetch_limit = 45
    search_results = await search_youtube_async(biased_query, limit=fetch_limit)
    if not search_results:
        return EnvelopeResponse(success=True, data=[])

    # 4. Score and filter videos
    filtered_videos = []
    rejected_count = 0
    for item in search_results:
        score = calculate_score(item['title'], item['channel'], trusted_channels)
        
        if not is_valid_nasheed(score):
            rejected_count += 1
            logger.debug(
                f"Filtered out: '{item['title']}' by '{item['channel']}' (score={score})"
            )
            continue

        # Upsert into videos table
        video_stmt = select(Video).where(Video.youtube_id == item['youtube_id'])
        video_res = await db.execute(video_stmt)
        existing_video = video_res.scalar_one_or_none()
        
        if existing_video:
            # Update attributes
            existing_video.title = item['title']
            existing_video.thumbnail = item['thumbnail']
            existing_video.duration = item['duration']
            existing_video.channel = item['channel']
            existing_video.score = score
            existing_video.upload_date = item['upload_date']
            video_obj = existing_video
        else:
            # Insert new video
            video_obj = Video(
                youtube_id=item['youtube_id'],
                title=item['title'],
                thumbnail=item['thumbnail'],
                duration=item['duration'],
                channel=item['channel'],
                score=score,
                upload_date=item['upload_date'],
                play_count=0
            )
            db.add(video_obj)
        
        filtered_videos.append(video_obj)

    logger.info(
        f"Search '{q}': {len(search_results)} fetched, "
        f"{rejected_count} rejected, {len(filtered_videos)} passed (threshold={settings.SCORE_THRESHOLD})"
    )
            
    try:
        await db.commit()
        # Refresh the instances to get generated primary keys and timestamps
        for video in filtered_videos:
            await db.refresh(video)
    except Exception as e:
        await db.rollback()
        raise SearchException(message=f"Failed to save results to database: {str(e)}")

    # Sort results by score (descending) so highest rated nasheeds appear first
    filtered_videos.sort(key=lambda x: x.score, reverse=True)

    # Cap to a reasonable return limit (15)
    filtered_videos = filtered_videos[:15]

    return EnvelopeResponse(
        success=True,
        data=[VideoResponse.model_validate(v) for v in filtered_videos]
    )

@router.get("/trending", response_model=EnvelopeResponse[List[VideoResponse]])
async def get_trending_nasheeds(
    limit: int = Query(15, ge=1, le=50, description="Number of trending items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Return popular nasheeds ordered by play_count, score, and creation date.
    Only includes videos that meet the minimum score threshold.
    """
    stmt = (
        select(Video)
        .where(Video.score >= settings.SCORE_THRESHOLD)
        .order_by(
            desc(Video.play_count),
            desc(Video.score),
            desc(Video.created_at)
        )
        .limit(limit)
    )
    res = await db.execute(stmt)
    videos = res.scalars().all()
    
    return EnvelopeResponse(
        success=True,
        data=[VideoResponse.model_validate(v) for v in videos]
    )
