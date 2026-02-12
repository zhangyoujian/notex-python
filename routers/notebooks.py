from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body
import json

from schemas.notebook import NotebookRequest, SourceRequest
from service.database import get_session
from service.vector import get_vector_service
from models import Notebook, User, Source, ChatSession, ChatMessage, Note
from crud.notebooks import *
from crud.source import *
from config import configer

from service.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])


async def check_notebook_access(user_id: int, notebook_id: str, db: AsyncSession):
    notebook = await db_get_notebook_by_id(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")
    if notebook.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return notebook

def get_notebook_info(notebook: Notebook):
    notebook_info = {
        "id": notebook.id,
        "user_id": notebook.user_id,
        "name": notebook.name,
        "description": notebook.description,
        "is_public": notebook.is_public,
        "public_token": notebook.public_token,
        "created_at": notebook.created_at,
        "updated_at": notebook.updated_at,
        "metadata": notebook.metadata_dict
    }
    return notebook_info


@router.get("")
async def handle_list_notebooks(user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_session)):
    """列出笔记本"""
    notebooks = await list_notebook_by_user_id(db, user.id)
    notebook_list = []

    for notebook in notebooks:
        notebook_list.append({
            "id": notebook.id,
            "user_id": notebook.user_id,
            "name": notebook.name,
            "description": notebook.notebook,
            "is_public": notebook.is_public,
            "public_token": notebook.public_token,
            "created_at": notebook.created_at,
            "updated_at": notebook.updated_at,
            "metadata": notebook.metadata_dict
        })

    return success_response(message="获取所有笔记信息成功", data=notebook_list)


@router.get("/stats")
async def handle_list_notebooks_with_stats(user: User = Depends(get_current_user),
                                           db: AsyncSession = Depends(get_session)):
    notebook_stat = await db_list_notebook_with_stats(db, user.id)
    return success_response(message="获取所有笔记状态成功", data=notebook_stat)


@router.post("")
async def handle_create_notebook(notebook_data: NotebookRequest,
                                 user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_session)):
    """创建笔记本"""
    notebook = await db_create_notebook(db,
                                        user.id,
                                        notebook_data.name,
                                        notebook_data.description,
                                        NotebookRequest.metadata_)

    return success_response(code=status.HTTP_201_CREATED, message="创建笔记成功", data=get_notebook_info(notebook))


@router.get("/{notebook_id}")
async def handle_get_notebook(notebook_id: str,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_session)):

    """获取笔记本详情"""
    notebook = await check_notebook_access(user.id, notebook_id, db)
    return success_response(message="获取笔记成功", data=get_notebook_info(notebook))


@router.put("/{notebook_id}")
async def handle_update_notebook(notebook_id: str,
                                 notebook_data: NotebookRequest,
                                 user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_session)):
    """更新笔记本"""
    notebook = await check_notebook_access(user.id, notebook_id, db)

    newbook = await db_update_notebook(db, notebook.id,
                                       notebook_data.name,
                                       notebook_data.description,
                                       notebook_data.metadata_)

    return success_response(message="更新笔记本成功", data=get_notebook_info(newbook))


@router.delete("/{notebook_id}")
async def handle_delete_notebook(notebook_id: str,
                                 user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_session)):
    """删除笔记本"""
    await check_notebook_access(user.id, notebook_id, db)

    await db_delete_notebook(db, notebook_id)

    return success_response(code=status.StatusNoContent, message="删除笔记本成功")


@router.put("/{notebook_id}/public")
async def handle_set_notebook_public(notebook_id: str,
                                     is_public: bool,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):
    """设置笔记本公开状态"""
    await check_notebook_access(user.id, notebook_id, db)

    new_book = await db_set_notebook_public(db, notebook_id, is_public)

    return success_response(message="设置笔记本为公开状态成功", data=get_notebook_info(new_book))


# 笔记本源文件管理
@router.get("/{notebook_id}/sources")
async def handle_list_sources(notebook_id: str,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_session)):
    """列出笔记本源文件"""
    await check_notebook_access(user.id, notebook_id, db)
    sources = await db_list_sources(db, notebook_id)
    if not sources:
        raise HTTPException(status_code=status.StatusInternalServerError, detail="Failed to list sources")

    source_list = []

    for source in sources:
        source_list.append({
            "id": source.id,
            "notebook_id": source.notebook_id,
            "name": source.name,
            "type": source.type,
            "url": source.url,
            "content": source.content,
            "file_name": source.file_name,
            "file_size": source.file_size,
            "chunk_count": source.chunk_count,
            "created_at": source.created_at,
            "updated_at": source.updated_at,
            "metadata": source.metadata_dict,
        })
    return success_response(message="列举公开资源信息成功", data=source_list)


@router.post("/{notebook_id}/sources")
async def handle_add_source(notebook_id: str,
                            source_data: SourceRequest,
                            user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_session),
                            vector_store = Depends(get_vector_service)):
    """添加源文件"""
    await check_notebook_access(user.id, notebook_id, db)

    if source_data.url and len(source_data.url) > 0:
        content = vector_store.extract_from_url(source_data.url)
        source_data.content = content

    source = await db_create_source(db, notebook_id,
                           source_data.name,
                           source_data.type,
                           source_data.url,
                           source_data.content,
                           "",
                           0,
                           configer.chunk_size,
                           source_data.metadata_)

    if source.content != "":
        chunk_count = vector_store.ingest_text(notebook_id, source.name, source.content)
        await db_update_source_chunk_count(db, source.id, chunk_count)

    data = {
        "id": source.id,
        "notebook_id": source.notebook_id,
        "name": source.name,
        "type": source.type,
        "url": source.url,
        "content": source.content,
        "file_name": source.file_name,
        "file_size": source.file_size,
        "chunk_count": source.chunk_count,
        "created_at": source.created_at,
        "updated_at": source.updated_at,
        "metadata": source.metadata_dict,
    }

    return success_response(message="添加资源成功", data=data)


@router.delete("/{notebook_id}/sources/{source_id}")
async def handle_delete_source(
    notebook_id: str,
    source_id: str,
    user: User = Depends(get_current_user)
):
    """删除源文件"""
    return {"deleted": True, "notebook_id": notebook_id, "source_id": source_id}


# 笔记管理
@router.get("/{notebook_id}/notes")
async def handle_list_notes(
    notebook_id: str,
    user: User = Depends(get_current_user)
):
    """列出笔记"""
    return {"notebook_id": notebook_id, "notes": []}


@router.post("/{notebook_id}/notes")
async def handle_create_note(
    notebook_id: str,
    data: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    """创建笔记"""
    return {"notebook_id": notebook_id, "note": data}


@router.delete("/{notebook_id}/notes/{note_id}")
async def handle_delete_note(
    notebook_id: str,
    note_id: str,
    user: User = Depends(get_current_user)
):
    """删除笔记"""
    return {"deleted": True, "notebook_id": notebook_id, "note_id": note_id}


# 转换
@router.post("/{notebook_id}/transform")
async def handle_transform(
    notebook_id: str,
    data: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    """执行转换"""
    return {"notebook_id": notebook_id, "transform_result": "transformed"}