from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ChatRequest(BaseModel):
    message: str
    session_id: str


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
