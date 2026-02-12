from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class NotebookRequest(BaseModel):
    name: str
    description: str
    metadata_: str


class SourceRequest(BaseModel):
    name: str
    type: str
    url: str
    content: str
    metadata_: str
