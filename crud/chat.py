from sqlalchemy import select, update, desc, delete, asc
from sqlalchemy.ext.asyncio import AsyncSession
from models.chat import ChatSession, ChatMessage


async def db_create_chat_session(db: AsyncSession,
                                 notebook_id: str,
                                 title="New Chat"):
    chat_session = ChatSession(notebook_id=notebook_id, title=title)
    db.add(chat_session)
    await db.commit()
    await db.refresh(chat_session)
    return chat_session


async def db_get_chat_session(db: AsyncSession, session_id: str):
    query = select(ChatSession).where(ChatSession.id == session_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def db_list_chat_sessions(db: AsyncSession, notebook_id: str):
    query = select(ChatSession).where(ChatSession.notebook_id == notebook_id).order_by(desc(ChatSession.updated_at))
    result = await db.execute(query)
    return result.scalars().all()


async def db_add_chat_message(db: AsyncSession, session_id: str, role: str, content: str, sources: str):
    chat_message = ChatMessage(session_id=session_id, role=role, content=content, sources=sources)
    db.add(chat_message)
    await db.commit()
    await db.refresh(chat_message)
    return chat_message


async def db_list_chat_messages(db: AsyncSession, session_id: str):
    query = select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(asc(ChatMessage.created_at))
    result = await db.execute(query)
    return result.scalars().all()


async def db_get_chat_message(db: AsyncSession, message_id: str):
    query = select(ChatMessage).where(ChatMessage.id == message_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def db_delete_chat_message(db: AsyncSession, message_id: str):
    stmt = delete(ChatMessage).where(ChatMessage.id == message_id)
    await db.execute(stmt)
    await db.commit()

