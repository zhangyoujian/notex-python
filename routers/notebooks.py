from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body
import json

from schemas.notebook import NotebookRequest
from service.database import get_session
from models import Notebook, User, Source, ChatSession, ChatMessage, Note
from crud.notebooks import *
from config import configer

from service.auth import get_current_user
from utils.response import success_response

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])


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
    notebook = await db_create_notebook(db, user.id,
                                        notebook_data.name,
                                        notebook_data.description,
                                        NotebookRequest.metadata_)

    notebook_info = {
        "id": notebook.id,
        "user_id": notebook.user_id,
        "name": notebook.name,
        "description": notebook.description,
        "is_public": notebook.is_public,
        "public_token": notebook.public_token,
        "created_at": notebook.created_at,
        "updated_at": notebook.updated_at,
        "metadata_": notebook.metadata_
    }
    return success_response(code=status.HTTP_201_CREATED, message="创建笔记成功", data=notebook_info)


@router.get("/{notebook_id}")
async def handle_get_notebook(notebook_id: str,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_session)):

    """获取笔记本详情"""
    notebook = await db_get_notebook_by_id(db, notebook_id)
    if not notebook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found")

    if notebook.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    notebook_info = {
        "id": notebook.id,
        "user_id": notebook.user_id,
        "name": notebook.name,
        "description": notebook.description,
        "is_public": notebook.is_public,
        "public_token": notebook.public_token,
        "created_at": notebook.created_at,
        "updated_at": notebook.updated_at,
        "metadata_": notebook.metadata_
    }
    return success_response(message="获取笔记成功", data=notebook_info)


@router.put("/{notebook_id}")
async def handle_update_notebook(
    notebook_id: str,
    data: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    """更新笔记本"""
    return {"id": notebook_id, "updated": True, **data}


@router.delete("/{notebook_id}")
async def handle_delete_notebook(
    notebook_id: str,
    user: User = Depends(get_current_user)
):
    """删除笔记本"""
    return {"deleted": True, "id": notebook_id}


@router.put("/{notebook_id}/public")
async def handle_set_notebook_public(
    notebook_id: str,
    data: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    """设置笔记本公开状态"""
    return {"id": notebook_id, "public": data.get("public", False)}


# 笔记本源文件管理
@router.get("/{notebook_id}/sources")
async def handle_list_sources(
    notebook_id: str,
    user: User = Depends(get_current_user)
):
    """列出笔记本源文件"""
    return {"notebook_id": notebook_id, "sources": []}


@router.post("/{notebook_id}/sources")
async def handle_add_source(
    notebook_id: str,
    data: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    """添加源文件"""
    return {"notebook_id": notebook_id, "source": data}


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