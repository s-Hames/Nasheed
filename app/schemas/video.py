from pydantic import BaseModel, ConfigDict
from datetime import datetime

class VideoBase(BaseModel):
    """
    Base properties for a Video entity.
    """
    youtube_id: str
    title: str
    thumbnail: str | None = None
    duration: int | None = None  # Duration in seconds
    channel: str
    score: int
    upload_date: str | None = None

class VideoCreate(VideoBase):
    """
    Schema for creating a video in the database.
    """
    pass

class VideoResponse(VideoBase):
    """
    Schema representing a video returned to the client.
    """
    id: int
    play_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
