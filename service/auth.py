from datetime import datetime, timedelta
from typing import Optional, Union, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from .database import get_session
from crud.users import db_get_user_by_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")  # Placeholder


async def get_current_user(token: str = Depends(oauth2_scheme), session: AsyncSession = Depends(get_session)) -> User:
    # credentials_exception = HTTPException(
    #     status_code=status.HTTP_401_UNAUTHORIZED,
    #     detail="Could not validate credentials",
    #     headers={"WWW-Authenticate": "Bearer"},
    # )
    user = await db_get_user_by_token(session, token)
    return user
