from fastapi import APIRouter, Depends
from service.database import get_session
from crud.notebooks import *
from crud.source import *
from crud.note import *
from .notebooks import get_notebook_info, get_source_info, get_note_info

from utils.response import success_response

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/notebooks")
async def handle_list_public_notebooks(db: AsyncSession = Depends(get_session)):
    notebook_list = []
    notebooks = await db_list_public_notebook(db, limit=100)
    if notebooks:
        for notebook in notebooks:
            # 获取关联数量（如果需要）
            source_count = len(notebook.sources) if notebook.sources else 0
            note_count = len(notebook.notes) if notebook.notes else 0
            notebook_list.append({
                'id': notebook.id,
                'user_id': notebook.user_id,
                'name': notebook.name,
                'description': notebook.description,
                'is_public': notebook.is_public,
                'public_token': notebook.public_token,
                'created_at': notebook.created_at,
                'updated_at': notebook.updated_at,
                'metadata': notebook.metadata_dict,
                'source_count': source_count,
                'note_count': note_count
            })

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


