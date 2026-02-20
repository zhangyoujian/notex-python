import json
from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional, Dict, Any
from schemas.notebook import NotebookRequest, SourceRequest, NoteRequest
from service.database import get_session
from service.notex_server import NotexServer, get_notex_server
from service.prompt import get_transformation_prompt
from service.vector_store import get_vector_service
from models.users import User
from crud.notebooks import *
from crud.source import *
from crud.note import *
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


def get_source_info(source: Source):
    source_info = {
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
    return source_info


def get_note_info(note: Note):
    note_info = {
        "id":note.id,
        "notebook_id": note.notebook_id,
        "title": note.title,
        "content": note.content,
        "type": note.type,
        "source_ids": note.source_ids,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "metadata_": note.metadata_dict
    }

    return note_info


@router.get("")
async def handle_list_notebooks(user: User = Depends(get_current_user),
                                db: AsyncSession = Depends(get_session)):
    """列出笔记本"""
    notebooks = await list_notebook_by_user_id(db, user.id)
    notebook_list = []

    for notebook in notebooks:
        notebook_list.append(get_notebook_info(notebook))

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
                                        "")

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

    updated_book = await db_update_notebook(db, notebook.id,
                                            notebook_data.name,
                                            notebook_data.description,
                                            notebook_data.metadata_)

    return success_response(message="更新笔记本成功", data=get_notebook_info(updated_book))


@router.delete("/{notebook_id}")
async def handle_delete_notebook(notebook_id: str,
                                 user: User = Depends(get_current_user),
                                 db: AsyncSession = Depends(get_session)):
    """删除笔记本"""
    await check_notebook_access(user.id, notebook_id, db)

    await db_delete_notebook(db, notebook_id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除笔记本成功")


@router.put("/{notebook_id}/public")
async def handle_set_notebook_public(notebook_id: str,
                                     is_public: bool,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):
    """设置笔记本公开状态"""
    await check_notebook_access(user.id, notebook_id, db)

    new_book = await db_set_notebook_public(db, notebook_id, is_public)

    return success_response(message="设置笔记本是否公开成功", data=get_notebook_info(new_book))


# 笔记本源文件管理
@router.get("/{notebook_id}/sources")
async def handle_list_sources(notebook_id: str,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_session)):
    """列出笔记本源文件"""
    await check_notebook_access(user.id, notebook_id, db)
    sources = await db_list_sources(db, notebook_id)
    if not sources:
        return success_response(message="列举公开资源信息成功")

    source_list = []
    for source in sources:
        source_list.append(get_source_info(source))
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

    source = await db_create_source(db,
                                    notebook_id,
                                    source_data.name,
                                    source_data.type,
                                    source_data.url,
                                    source_data.content,
                                    "",
                                    0,
                                    0,
                                    source_data.metadata)

    if source.content != "":
        chunk_count = vector_store.ingest_text(notebook_id, source.name, source.content)
        await db_update_source_chunk_count(db, source.id, chunk_count)

    return success_response(code=status.HTTP_201_CREATED, message="添加资源成功", data=get_source_info(source))


@router.delete("/{notebook_id}/sources/{source_id}")
async def handle_delete_source(notebook_id: str,
                               source_id: str,
                               user: User = Depends(get_current_user),
                               db: AsyncSession = Depends(get_session)):
    """删除源文件"""
    source = await db_get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    await check_notebook_access(source.user_id, source.notebook_id, db)

    await db_delete_source(db, source.id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除资源成功")


# 笔记管理
@router.get("/{notebook_id}/notes")
async def handle_list_notes(notebook_id: str,
                            user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_session)):
    """列出笔记"""
    notes = await db_list_notes(db, notebook_id)
    notex_list = []
    for note in notes:
        notex_list.append(get_note_info(note))

    return success_response(message="获取笔记信息列表成功", data=notex_list)


@router.post("/{notebook_id}/notes")
async def handle_create_note(notebook_id: str,
                             note_data: NoteRequest,
                             user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_session)):
    """创建笔记"""
    note = await db_create_note(db,
                                notebook_id,
                                note_data.title,
                                note_data.content,
                                note_data.type,
                                note_data.source_ids,
                      "")
    return success_response(code=status.HTTP_201_CREATED, message="创建笔记成功", data=get_note_info(note))


@router.delete("/{notebook_id}/notes/{note_id}")
async def handle_delete_note(notebook_id: str,
                             note_id: str,
                             user: User = Depends(get_current_user),
                             db: AsyncSession = Depends(get_session)):
    """删除笔记"""

    await db_delete_note(db, note_id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除笔记成功")


# 转换
@router.post("/{notebook_id}/transform")
async def handle_transform(notebook_id: str,
                           payload: Dict[str, Any] = Body(...),
                           user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_session),
                           server: NotexServer = Depends(get_notex_server)):

    """执行转换"""
    # 按需加载向量索引
    await server.load_notebook_vector_index(notebook_id, db)
    if not configer.allow_multiple_notes_of_same_type:
        existing_notes = await db_list_notes(db, notebook_id)
        for note in existing_notes:
            if note.type == payload.get('type', ""):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该笔记本已存在相同类型的笔记，不允许创建重复类型")

    sources = await db_list_sources(db, notebook_id)
    source_ids = payload.get("source_ids") or []
    length = payload.get("length") or "medium"
    format_ = payload.get("format") or "markdown"
    type_ = payload.get("type", "summary")

    if len(source_ids) > 0:
        filtered = []
        source_map = {}
        for source_id in source_ids:
            source_map[source_id] = True

        for source in sources:
            if source_map[source.id]:
                filtered.append(get_source_info(source))

    else:
        payload["source_ids"] = {}
        index = 0
        for source in sources:
            payload["source_ids"][index] = source.id
            index += 1

    if len(sources) == 0:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="No sources available")

    contents = [s.content or "" for s in sources]
    ctx = "\n\n".join(contents)
    instruction = get_transformation_prompt(type_)
    base_prompt = f"资料如下：\n\n{ctx}\n\n要求：{instruction}\n长度偏好：{length}；格式：{format_}。"

    response = await server.agent.generate_text(base_prompt)

    title_map = {
        "summary": "摘要",
        "faq": "常见问题",
        "study_guide": "学习指南",
        "outline": "大纲",
        "ppt": "幻灯片",
        "glossary": "术语表",
        "quiz": "测验",
        "mindmap": "思维导图",
        "infograph": "信息图",
        "timeline": "时间线",
        "custom": "自定义"
    }
    title = f"{title_map.get(type_, '内容')}"

    note = await db_create_note(db, notebook_id, title, response, type_, json.dumps(source_ids), "")

    return success_response(message="生成transofrm成功", data=get_note_info(note))
