import uuid
from datetime import datetime, timedelta
from starlette import status
from fastapi import HTTPException
from sqlalchemy import select, update, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserToken
from schemas.users import RegisterRequest, UpdateRequest
from utils import security
from utils.security import check_password_complexity


# 创建用户
async def db_create_user(db: AsyncSession, user_data: RegisterRequest):
    # 先密码加密处理 → add
    hashed_password = security.get_hash_password(user_data.password)
    user = User(email=user_data.email, username=user_data.username, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)  # 从数据库读回最新的 user
    return user


async def db_delete_user(db: AsyncSession, user_id: int):
    stmt = delete(User).where(User.id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


# 根据用户名查询数据库
async def db_get_user_by_email(db: AsyncSession, email: str):
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# 根据用户id获取用户
async def db_get_user_by_user_id(db: AsyncSession, user_id: int):
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# 生成 Token
async def db_create_token(db: AsyncSession, user_id: int):
    # 生成 Token + 设置过期时间 → 查询数据库当前用户是否有 Token → 有：更新；没有：添加
    token = str(uuid.uuid4())
    # timedelta(days=7, hours=2, minutes=30, seconds=10)
    expires_at = datetime.now() + timedelta(days=0, hours=12)
    query = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()

    if user_token:
        user_token.token = token
        user_token.expires_at = expires_at
    else:
        user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(user_token)
        await db.commit()

    return token


async def db_authenticate_user(db: AsyncSession, email: str, password: str):
    user = await db_get_user_by_email(db, email)
    if not user:
        return None
    if not security.verify_password(password, user.password):
        return None

    return user


# 根据 Token 查询用户：验证 Token → 查询用户
async def db_get_user_by_token(db: AsyncSession, token: str):
    query = select(UserToken).where(UserToken.token == token)
    result = await db.execute(query)
    db_token = result.scalar_one_or_none()

    if not db_token or db_token.expires_at < datetime.now():
        return None

    query = select(User).where(User.id == db_token.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def db_list_all_users(db: AsyncSession):
    """获取所有用户（按创建时间倒序）"""
    query = select(User).order_by(desc(User.created_at))
    result = await db.execute(query)
    return result.scalars().all()


async def db_update_user(db: AsyncSession, user_id: int, user_data: UpdateRequest):

    if not user_data.password or user_data.password == "":
        stmt = update(User).where(User.id == user_id).values(username=user_data.username)
    else:
        is_ok, detail = check_password_complexity(user_data.password)
        if not is_ok:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

        new_passwd = security.get_hash_password(user_data.password)
        stmt = update(User).where(User.id == user_id).values(username=user_data.username, password=new_passwd)

    # 更新用户名或密码
    result = await db.execute(stmt)
    await db.commit()

    # 检查更新
    if result.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 更新用户token
    await db_create_token(db, user_id)

    updated_user = await db_get_user_by_user_id(db, user_id)
    return updated_user

