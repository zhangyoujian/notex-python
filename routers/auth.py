from fastapi import APIRouter, Depends
from starlette import status

from schemas.users import UserAuthResponse, UserInfoResponse

from service.database import get_session
from crud.users import *
from utils.response import success_response

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def handle_me(user_id: int, db: AsyncSession = Depends(get_session)):
    user = await db_get_user_by_user_id(db, user_id)
    user_info = {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "avatar": user.avatar
    }
    return success_response(message="获取用户信息成功", data=user_info)


@router.post("/register")
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_session)):  # 用户信息 和 db
    # 注册逻辑：验证用户是否存在 -> 创建用户 → 生成 Token  → 响应结果
    existing_user = await db_get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")

    user = await db_create_user(db, user_data)
    token = await db_create_token(db, user.id)
    response_data = UserAuthResponse(token=token, user=UserInfoResponse.model_validate(user))
    return success_response(message="注册成功", data=response_data)


@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_session)):
    # 登录逻辑：验证用户是否存在 -> 验证密码 -> 生成 Token  → 响应结果
    user = await db_authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = await db_create_token(db, user.id)
    response_data = UserAuthResponse(token=token, user=UserInfoResponse.model_validate(user))
    return success_response(message="登录成功", data=response_data)


