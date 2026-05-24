from pydantic import BaseModel

class HealthResponse(BaseModel):
    """
    Schema for health status response.
    """
    status: str
    database: str
