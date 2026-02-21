import uuid
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select, update, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.source import Source
from utils import logger


async def db_create_source(db: AsyncSession,
                             notebook_id: str,
                             name: str,
                             type_: str,
                             url: str,
                             content: str,
                             file_name: str,
                             file_size: int,
                             chunk_count: int,
                             metadata_: str):
    source = Source(notebook_id=notebook_id,
                    name=name,
                    type=type_,
                    url=url,
                    content=content,
                    file_name=file_name,
                    file_size=file_size,
                    chunk_count=chunk_count,
                    metadata_=metadata_
                    )
    db.add(source)
    await db.commit()
    await db.refresh(source)  # 从数据库读回最新的 user
    return source


async def db_get_source_by_id(db: AsyncSession, source_id: str):
    query = select(Source).where(Source.id == source_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def db_get_source_by_filename(db: AsyncSession, file_name: str):
    query = select(Source).where(Source.file_name == file_name)
    result = await db.execute(query)
    return result.scalars().all()


async def db_list_sources(db: AsyncSession, notebook_id: str):
    query = select(Source).where(Source.notebook_id == notebook_id).order_by(desc(Source.created_at))
    result = await db.execute(query)
    return result.scalars().all()


async def db_delete_source(db: AsyncSession, source_id: str):
    stmt = delete(Source).where(Source.id == source_id)
    await db.execute(stmt)
    await db.commit()


async def db_update_source_chunk_count(db: AsyncSession, source_id: str, chunk_count: int):
    stmt = update(Source).where(Source.id==source_id).values(chunk_count=chunk_count)
    result = await db.execute(stmt)
    if result.rowcount <= 0:
        logger.error(f"update source chunk count failed.")
    await db.commit()


