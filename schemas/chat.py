from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class SourceSummary(BaseModel):
    id: str
    name: str
    type: str


class ChatResponse(BaseModel):
    message: str
    sources: list[SourceSummary]
    session_id: str
    message_id: str
    metadata_: str
