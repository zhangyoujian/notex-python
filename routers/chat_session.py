import json
from fastapi import APIRouter, Depends, HTTPException, status, Body

from schemas.notebook import NotebookRequest, SourceRequest, NoteRequest
from service.database import get_session
from service.vector_store import get_vector_service
from models.chat import ChatSession, ChatMessage
from models.notebook import Notebook
from models.users import User
from crud.chat import *
from config import configer
from schemas.chat import ChatRequest

from service.auth import get_current_user
from utils.response import success_response
from service.notex_server import NotexServer, get_notex_server

from .notebooks import router


def get_session_info(session: ChatSession):
    return {
        "id": session.id,
        "notebook_id": session.notebook_id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "metadata": session.metadata_
    }


@router.get("/{notebook_id}/chat/sessions")
async def handle_list_chat_session(notebook_id: str,
                                   user: User = Depends(get_current_user),
                                   db: AsyncSession = Depends(get_session)):
    sessions = await db_list_chat_sessions(db, notebook_id)
    session_list = []
    for session in sessions:
        session_list.append(get_session_info(session))

    return success_response("列举回话信息成功", data=session_list)


@router.post("/{notebook_id}/chat/sessions")
async def handle_create_chat_session(notebook_id: str,
                                     title: str,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):
    session = await db_create_chat_session(db, notebook_id, title)

    return success_response(code=status.HTTP_201_CREATED, message="创建新会话成功", data=get_session_info(session))


@router.delete("/{notebook_id}/chat/sessions/{session_id}")
async def handle_delete_chat_session(notebook_id: str,
                                     session_id: str,
                                     user: User = Depends(get_current_user),
                                     db: AsyncSession = Depends(get_session)):
    await db_delete_chat_session(db, session_id)

    return success_response(code=status.HTTP_204_NO_CONTENT, message="删除会话成功")


@router.post("/{notebook_id}/chat/sessions/{session_id}/messages")
async def handle_send_message(notebook_id: str,
                              chat_request: ChatRequest,
                              user: User = Depends(get_current_user),
                              db: AsyncSession = Depends(get_session),
                              server: NotexServer = Depends(get_notex_server)):


    await server.load_notebook_vector_index(notebook_id, db)

    # Create or get session
    session_id = chat_request.session_id
    if session_id == "":
        session = await db_create_chat_session(db, notebook_id, "")
        session_id = session.id

    # Get session history
    session = await db_get_chat_session(db, session_id)

    # Generate response
    response = await server.agent.generate_chat(notebook_id, chat_request.message, session.messages)
    response.session_id = session_id

    sources_ids = []
    for ids in response.sources:
        sources_ids.append(ids.id)

    await db_add_chat_message(db, session_id, "user", chat_request.message, "")
    await db_add_chat_message(db, session_id, "assistant", response.message, json.dump(sources_ids, ensure_ascii=False))


    return success_response(message="发送消息成功", data=response)


@router.post("/{notebook_id}/chat")
async def handle_chat(notebook_id: str,
                      chat_request: ChatRequest,
                      user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_session),
                      server: NotexServer = Depends(get_notex_server)):

    await server.load_notebook_vector_index(notebook_id, db)

    # Create or get session
    session_id = chat_request.session_id
    if session_id == "":
        session = await db_create_chat_session(db, notebook_id, "")
        session_id = session.id

    # Get session history
    session = await db_get_chat_session(db, session_id)

    # Generate response
    response = await server.agent.chat(notebook_id, chat_request.message, session.messages)
    response.session_id = session_id

    sources_ids = []
    for ids in response.sources:
        sources_ids.append(ids.id)

    await db_add_chat_message(db, session_id, "user", chat_request.message, "")
    await db_add_chat_message(db, session_id, "assistant", response.message,
                              json.dump(sources_ids, ensure_ascii=False))

    return success_response(message="发送消息成功", data=response)