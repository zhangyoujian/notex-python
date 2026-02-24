import json
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pathlib import Path
from crud.chat import db_add_chat_message, db_get_chat_session, db_create_chat_session, db_delete_chat_session, \
    db_list_chat_sessions
from schemas.chat import ChatRequest
from schemas.notebook import NotebookRequest, SourceRequest, NoteRequest, TransformationRequest
from service.database import get_session
from service.notex_server import NotexServer, get_notex_server
from models.users import User
from models.chat import ChatSession
from crud.notebooks import *
from crud.source import *
from crud.note import *
from config import configer

from service.auth import get_current_user
from utils.response import success_response
from utils.convert import *

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


def get_session_info(session: ChatSession):
    return {
        "id": session.id,
        "notebook_id": session.notebook_id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "metadata": session.metadata_
    }

def _get_title_for_type(t: str) -> str:
    """获取转换类型的中文标题"""
    titles = {
        "summary": "摘要",
        "faq": "常见问题解答",
        "study_guide": "学习指南",
        "outline": "大纲",
        "podcast": "播客脚本",
        "timeline": "时间线",
        "glossary": "术语表",
        "quiz": "测验",
        "infograph": "信息图",
        "ppt": "幻灯片",
        "mindmap": "思维导图",
        "insight": "洞察报告",
    }
    return titles.get(t, "笔记")

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

    notebooks = await db_list_notebook_with_stats(db, user.id)
    notebook_list = []
    for notebook in notebooks:
        source_count = len(notebook.sources) if notebook.sources else 0
        note_count = len(notebook.notes) if notebook.notes else 0
        notebook_list.append({
            "id": notebook.id,
            "user_id": notebook.user_id,
            "name": notebook.name,
            "description": notebook.description,
            "is_public": notebook.is_public,
            "public_token": notebook.public_token,
            "created_at": notebook.created_at,
            "updated_at": notebook.updated_at,
            "metadata": notebook.metadata_dict,
            "source_count": source_count,
            "note_count": note_count
        })
    return success_response(message="获取所有笔记状态成功", data=notebook_list)


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
                                            notebook.metadata_)

    return success_response(message="更新笔记本成功", data=get_notebook_info(updated_book))


@router.delete("/{notebook_id}")
async def handle_delete_notebook(notebook_id: str,
                                 user: User = Depends(get_current_user),
                                 notex_server: NotexServer = Depends(get_notex_server),
                                 db: AsyncSession = Depends(get_session)):
    """删除笔记本"""
    await check_notebook_access(user.id, notebook_id, db)

    await db_delete_notebook(db, notebook_id)

    # 删除向量数据
    await notex_server.remove_notebook_vector_index(notebook_id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除笔记本成功")


@router.put("/{notebook_id}/public")
async def handle_set_notebook_public(notebook_id: str,
                                     is_public: bool = Body(..., embed=True),
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
        return success_response(message="列举公开资源信息成功", data=[])

    source_list = []
    for source in sources:
        source_list.append(get_source_info(source))
    return success_response(message="列举公开资源信息成功", data=source_list)


@router.post("/{notebook_id}/sources")
async def handle_add_source(notebook_id: str,
                            source_data: SourceRequest,
                            user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_session),
                            notex_server: NotexServer = Depends(get_notex_server)):
    """添加源文件"""
    await check_notebook_access(user.id, notebook_id, db)

    if source_data.url and len(source_data.url) > 0:
        try:
            content = await extract_from_url(source_data.url)
            source_data.content = content
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="无效的URL或者当前URL被禁止爬取")

    metadata_json = json.dumps(source_data.metadata) if source_data.metadata else "{}"
    source = await db_create_source(db,
                                    notebook_id,
                                    source_data.name,
                                    source_data.type,
                                    source_data.url,
                                    source_data.content,
                                    "",
                                    0,
                                    0,
                                    metadata_json)

    if source.content != "":
        chunk_count = notex_server.vector_store.ingest_text(notebook_id, source.name, source.content)
        await db_update_source_chunk_count(db, source.id, chunk_count)

    return success_response(code=status.HTTP_201_CREATED, message="添加资源成功", data=get_source_info(source))


@router.delete("/{notebook_id}/sources/{source_id}")
async def handle_delete_source(notebook_id: str,
                               source_id: str,
                               user: User = Depends(get_current_user),
                               notex_server: NotexServer = Depends(get_notex_server),
                               db: AsyncSession = Depends(get_session)):
    """删除源文件"""
    source = await db_get_source_by_id(db, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    await check_notebook_access(user.id, source.notebook_id, db)

    # 从向量数据库中移除
    notex_server.vector_store.delete(notebook_id, source.name)

    await db_delete_source(db, source.id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除资源成功")


# 笔记管理
@router.get("/{notebook_id}/notes")
async def handle_list_notes(notebook_id: str,
                            user: User = Depends(get_current_user),
                            db: AsyncSession = Depends(get_session)):
    """列出笔记"""
    notes = await db_list_notes(db, notebook_id)
    if not notes:
        return success_response(message="获取笔记信息列表成功", data=[])

    await check_notebook_access(user.id, notebook_id, db)

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
    await check_notebook_access(user.id, notebook_id, db)

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
    await check_notebook_access(user.id, notebook_id, db)

    await db_delete_note(db, note_id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除笔记成功")


# 转换
@router.post("/{notebook_id}/transform")
async def handle_transform(notebook_id: str,
                           req: TransformationRequest,
                           user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_session),
                           server: NotexServer = Depends(get_notex_server)):

    """执行转换"""
    # 按需加载向量索引
    await check_notebook_access(user.id, notebook_id, db)
    await server.load_notebook_vector_index(notebook_id, db)

    if not configer.allow_multiple_notes_of_same_type:
        existing_notes = await db_list_notes(db, notebook_id)
        for note in existing_notes:
            if note.type == req.type:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该笔记本已存在相同类型的笔记，不允许创建重复类型")

    sources = await db_list_sources(db, notebook_id)

    if req.source_ids:
        source_map = {s.id: s for s in sources}
        sources = [source_map[sid] for sid in req.source_ids if sid in source_map]
    else:
        req.source_ids = [s.id for s in sources]
    if not sources:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sources available")

    try:
        response = await server.agent.generate_transformation(req, sources)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Generation failed: {e}")

    metadata = {
        "length": req.length,
        "format": req.format
    }
    if req.type == "infograph" and server.agent.gemini:
        try:
            extra = "**注意：无论来源是什么语言，请务必使用中文**"
            prompt = response.content + "\n\n" + extra
            image_path = await server.agent.gemini.generate_image("gemini-3-pro-image-preview", prompt)
            web_path = "/uploads/" + Path(image_path).name
            metadata["image_url"] = web_path
        except Exception as e:
            logger.error(f"failed to generate infographic image: {e}")
            metadata["image_error"] = str(e)

    if req.type == "ppt" and server.agent.gemini:
        slides = server.agent.parse_ppt_slides(response.content)
        if len(slides) > 10:
            logger.error(f"ppt contains too many slides ({len(slides)}), maximum allowed is 20. skipping image generation.")
            metadata["image_error"] = "PPT页数超过20页上限，已停止生成图片"
        else:
            slide_urls = []
            logger.info(f"generating {len(slides)} slides for ppt...")

            for i, slide in enumerate(slides):
                logger.info(f"generating image for slide {i + 1}/{len(slides)}...")
                try:
                    prompt = f"Style: {slides[0].style}\n\nSlide Content: {slide.content}"
                    prompt += "\n\n**注意：无论来源是什么语言，请务必使用中文**\n"
                    image_path = await server.agent.gemini.generate_image("gemini-3-pro-image-preview", prompt)
                    slide_urls.append("/uploads/" + Path(image_path).name)
                except Exception as e:
                    logger.error(f"failed to generate slide {i + 1}: {e}")
                    continue
            metadata["slides"] = slide_urls

    # 保存为 note
    note_content = response.content
    if req.type == "infograph":
        note_content = ""  # infograph 只显示图片

    created_note = await db_create_note(db,
                                        notebook_id,
                                        _get_title_for_type(req.type),
                                        note_content,
                                        req.type,
                                        json.dumps(req.source_ids, ensure_ascii=False),
                                        json.dumps(metadata, ensure_ascii=False))

    if req.type == "insight":
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "source_ids": req.source_ids
        }
        try:
            created_insight = await db_create_source(db,
                                                     notebook_id,
                                                     "洞察报告",
                                                     "insight",
                                                     "",
                                                     response.content,
                                                     "",
                                                     0,
                                                     0,
                                                     json.dumps(metadata, ensure_ascii=False)
                                                     )
            chunk_count = await server.vector_store.ingest_text(notebook_id, created_insight.name, created_insight.content)
            await db_update_source_chunk_count(db, created_insight.id, chunk_count)
        except Exception as e:
            logger.error(f"failed to create insight source: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"failed to create insight source: {e}")
            
    return success_response(message="生成transform成功", data=get_note_info(created_note))


@router.get("/{notebook_id}/chat/sessions")
async def handle_list_chat_session(notebook_id: str,
                                   user: User = Depends(get_current_user),
                                   db: AsyncSession = Depends(get_session)):
    await check_notebook_access(user.id, notebook_id, db)

    sessions = await db_list_chat_sessions(db, notebook_id)
    if not sessions:
        return success_response("列举会话信息成功", data=[])

    session_list = []
    for session in sessions:
        session_list.append(get_session_info(session))

    return success_response("列举会话信息成功", data=session_list)


@router.post("/{notebook_id}/chat/sessions")
async def handle_create_chat_session(notebook_id: str,
                                     title: str,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):

    await check_notebook_access(user.id, notebook_id, db)

    session = await db_create_chat_session(db, notebook_id, title)

    return success_response(code=status.HTTP_201_CREATED, message="创建新会话成功", data=get_session_info(session))


@router.delete("/{notebook_id}/chat/sessions/{session_id}")
async def handle_delete_chat_session(notebook_id: str,
                                     session_id: str,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):
    await check_notebook_access(user.id, notebook_id, db)

    await db_delete_chat_session(db, session_id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除会话成功")


@router.post("/{notebook_id}/chat/sessions/{session_id}/messages")
async def handle_send_message(notebook_id: str,
                              session_id: str,
                              chat_request: ChatRequest,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_session),
                              server: NotexServer = Depends(get_notex_server)):

    await check_notebook_access(user.id, notebook_id, db)

    await server.load_notebook_vector_index(notebook_id, db)

    await db_add_chat_message(db, session_id, "user", chat_request.message, "")

    # 获取历史消息
    session = await db_get_chat_session(db, session_id)

    # 知识库检索
    docs = server.vector_store.similarity_search(notebook_id, chat_request.message)

    # 2. 构建上下文文本
    source_ids_set = set()
    context_text = ""
    for i, doc in enumerate(docs):
        context_text += f"[来源 {i + 1}] {doc.page_content}\n"
        source = doc.metadata.get("source", None)
        if source:
            source_ids_set.add(source)
            context_text += f"来源: {source}\n\n"

    history_msg = session.messages
    sources_ids = list(source_ids_set)

    response = await server.agent.generate_chat(notebook_id, chat_request.message, history_msg, context_text)

    await db_add_chat_message(db, session_id, "assistant", response, json.dumps(sources_ids, ensure_ascii=False))

    result = {
        "session_id": session_id,
        "message": response,
        "sources": sources_ids
    }
    return success_response(message="发送消息成功", data=result)


@router.post("/{notebook_id}/chat")
async def handle_chat(notebook_id: str,
                      chat_request: ChatRequest,
                      user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_session),
                      server: NotexServer = Depends(get_notex_server)):

    await check_notebook_access(user.id, notebook_id, db)

    await server.load_notebook_vector_index(notebook_id, db)

    # Create or get session
    session_id = chat_request.session_id
    if not session_id:
        title = "New Chat" if len(chat_request.message) == 0 else chat_request.message[:min(32, len(chat_request.message))]
        session = await db_create_chat_session(db, notebook_id, title=title)
        session_id = session.id
    else:
        # Get session history
        session = await db_get_chat_session(db, session_id)

    # 知识库检索
    docs = server.vector_store.similarity_search(notebook_id, chat_request.message)

    # 2. 构建上下文文本
    source_ids_set = set()
    context_text = ""
    for i, doc in enumerate(docs):
        context_text += f"[来源 {i + 1}] {doc.page_content}\n"
        source = doc.metadata.get("source", None)
        if source:
            source_ids_set.add(source)
            context_text += f"来源: {source}\n\n"

    history_msg = session.messages
    response_text = await server.agent.generate_chat(notebook_id, chat_request.message, history_msg, context_text)

    sources_ids = list(source_ids_set)

    await db_add_chat_message(db, session_id, "user", chat_request.message, "")
    await db_add_chat_message(db, session_id, "assistant", response_text, json.dumps(sources_ids, ensure_ascii=False))

    result = {
        "session_id": session_id,
        "message": response_text,
        "sources": sources_ids
    }
    return success_response(message="发送消息成功", data=result)