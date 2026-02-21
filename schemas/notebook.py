from typing import Optional
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class NotebookRequest(BaseModel):
    name: str
    description: str


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
