from typing import Optional
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class NotebookRequest(BaseModel):
    name: str
    description: Optional[str] = None


class SourceRequest(BaseModel):
    name: str
    type: str
    url: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NoteRequest(BaseModel):
    title: str
    content: str
    type: str
    source_ids: str


class SourceSummary(BaseModel):
    """来源摘要"""
    id: str
    name: str
    type: str

class TransformationResponse(BaseModel):
    """内容转换响应"""
    type: str
    content: str
    sources: List[SourceSummary]
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TransformationRequest(BaseModel):
    """内容转换请求"""
    type: str
    prompt: Optional[str] = None
    source_ids: List[str] = Field(default_factory=list)
    length: str = "medium"
    format: str = "markdown"
