from sqlalchemy import select, update, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.notebook import Notebook, Note
from utils import logger
from models.base import generate_uuid


async def db_create_notebook(db: AsyncSession, user_id: int, name: str, description: str, metadata: str):
    notebook = Notebook(user_id=user_id, name=name, description=description, metadata_=metadata)
    db.add(notebook)
    await db.commit()
    await db.refresh(notebook)  # 从数据库读回最新的 user
    return notebook


async def db_get_notebook_by_id(db: AsyncSession, notebook_id: str):
    query = select(Notebook).where(Notebook.id == notebook_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_notebook_by_user_id(db: AsyncSession, user_id: int,  skip: int = 0, limit: int = 10000):
    query = select(Notebook).where(Notebook.user_id == user_id).order_by(desc(Notebook.updated_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def db_update_notebook(db: AsyncSession, notebook_id: str, name: str, description: str, metadata: str):
    stmt = update(Notebook).where(id=notebook_id).values(name=name, description=description, metadata=metadata)
    result = await db.execute(stmt)
    if result.rowcount <= 0:
        logger.error(f"update notebook failed.")
    await db.commit()
    ret = await db_get_notebook_by_id(db, notebook_id)
    return ret


async def db_set_notebook_public(db: AsyncSession, notebook_id: str, is_public: bool):
    if is_public:
        stmt = update(Notebook).where(Notebook.id==notebook_id).values(is_public=1, public_token=generate_uuid())
    else:
        stmt = update(Notebook).where(Notebook.id==notebook_id).values(is_public=0, public_token=None)

    result = await db.execute(stmt)
    if result.rowcount <= 0:
        logger.error(f"set notebook public failed.")
    await db.commit()
    ret = await db_get_notebook_by_id(db, notebook_id)
    return ret


async def db_get_notebook_by_public_token(db: AsyncSession, token: str):
    query = select(Notebook).where((Notebook.public_token == token) & (Notebook.is_public == 1))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def db_delete_notebook(db: AsyncSession, notebook_id: str):
    stmt = delete(Notebook).where(Notebook.id == notebook_id)
    await db.execute(stmt)
    await db.commit()


async def db_list_notebook_with_stats(db: AsyncSession, user_id: int):
    query = (
        select(Notebook)
        .where(Notebook.user_id == user_id)
        .options(
    selectinload(Notebook.sources),
            selectinload(Notebook.notes)
        )
        .order_by(desc(Notebook.updated_at))
    )
    result = await db.execute(query)
    notebooks = result.scalars().all()
    return notebooks

async def db_list_public_notebook(db: AsyncSession, skip: int = 0, limit: int = 20):
    """异步简化版本 - 推荐使用"""
    stmt = (
        select(Notebook)
        .distinct()
        .join(Note, Note.notebook_id == Notebook.id)
        .where(Notebook.is_public == 1)
        .where(Note.type.in_(['infograph', 'ppt']))
        .options(selectinload(Notebook.sources), selectinload(Notebook.notes))
        .order_by(Notebook.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(stmt)
    notebooks = result.scalars().all()

    return notebooks





