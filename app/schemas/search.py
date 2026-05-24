from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar('T')

class EnvelopeResponse(BaseModel, Generic[T]):
    """
    Standardized API envelope for all successful responses.
    """
    success: bool = True
    data: T

class SearchHistoryResponse(BaseModel):
    """
    Schema representing a recorded search query in the history database.
    """
    id: int
    query: str
    hit_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StreamResponse(BaseModel):
    """
    Schema for streaming endpoint responses containing the extracted audio URL.
    """
    video_id: str
    stream_url: str
