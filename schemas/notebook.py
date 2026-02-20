from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class NotebookRequest(BaseModel):
    name: str
    description: str


class SourceRequest(BaseModel):
    name: str
    type: str
    url: str
    content: str
    metadata: Optional[str]


class NoteRequest(BaseModel):
    title: str
    content: str
    type: str
    source_ids: str
