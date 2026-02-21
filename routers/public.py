from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body
import json

from schemas.notebook import NotebookRequest, SourceRequest, NoteRequest
from service.database import get_session
from models import Notebook, User, Note
from crud.notebooks import *
from crud.source import *
from crud.note import *
from config import configer
from .notebooks import get_notebook_info, get_source_info, get_note_info

from service.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/notebooks")
async def handle_list_public_notebooks(db: AsyncSession = Depends(get_session)):

    notebooks = await db_list_public_notebook(db, limit=100)
    notebook_list = []
    if notebooks:
        for notebook in notebooks:
            notebook_list.append(get_notebook_info(notebook))

    return success_response(message="获取公共笔记列表成功", data=notebook_list)


@router.get("/notebooks/{token}")
async def handle_get_public_notebooks(token: str,
                                      db: AsyncSession = Depends(get_session)):
    notebook = await db_get_notebook_by_public_token(db, token)

    return success_response(message="获取公共笔记成功", data=get_notebook_info(notebook))


@router.get("/notebooks/{token}/sources")
async def handle_list_public_sources(token: str,
                                     db: AsyncSession = Depends(get_session)):
    notebook = await db_get_notebook_by_public_token(db, token)

    sources = await db_list_sources(db, notebook.id)
    source_list = []
    for source in sources:
        source_list.append(get_source_info(source))

    return success_response(message="获取公共资源列表成功", data=source_list)


@router.get("/notebooks/{token}/notes")
async def handle_list_public_notes(token: str,
                                   db: AsyncSession = Depends(get_session)):
    notebook = await db_get_notebook_by_public_token(db, token)

    notes = await db_list_notes(db, notebook.id)
    note_list = []
    for note in notes:
        note_list.append(get_note_info(note))

    return success_response(message="获取公共笔记列表成功", data=note_list)


