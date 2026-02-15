from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body
import json

from schemas.notebook import NotebookRequest, SourceRequest, NoteRequest
from service.database import get_session
from service.vector import get_vector_service
from models import Notebook, User, Note
from crud.notebooks import *
from crud.source import *
from crud.note import *
from config import configer

from service.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/notebooks")
async def handle_list_public_notebooks(user: User = Depends(get_current_user),
                                       db: AsyncSession = Depends(get_session)):
    return success_response()


@router.get("/notebooks/{token}")
async def handle_get_public_notebooks(token: str,
                                      user: User = Depends(get_current_user),
                                      db: AsyncSession = Depends(get_session)):
    return success_response()


@router.get("/notebooks/{token}/sources")
async def handle_list_public_sources(token: str,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):
    return success_response()


@router.get("/notebooks/{token}/notes")
async def handle_list_public_notes(token: str,
                                   user: User = Depends(get_current_user),
                                   db: AsyncSession = Depends(get_session)):
    return success_response()



