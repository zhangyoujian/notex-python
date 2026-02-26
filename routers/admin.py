from fastapi import APIRouter, Depends
from service.database import get_session
from crud.users import *
from utils.response import success_response
from utils.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_user_info(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at
    }


@router.get("/users")
async def list_users(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_session)):
    """获取所有用户列表（仅管理员）"""
    users = await db_list_all_users(db)
    user_list = []
    for user in users:
        user_list.append(get_user_info(user))
    return success_response(message="获取用户列表成功", data=user_list)


@router.put("/users/{user_id}")
async def update_user(user_id: int, user_data: UpdateRequest,
                      admin: User = Depends(get_current_admin),
                      db: AsyncSession = Depends(get_session)):
    """更新用户信息（用户名、密码）"""

    updated_user = await db_update_user(db, user_id, user_data)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    return success_response(message="更新用户信息成功", data=get_user_info(updated_user))


@router.delete("/users/{user_id}")
async def delete_user(user_id: int,
                      admin: User = Depends(get_current_admin),
                      db: AsyncSession = Depends(get_session)):
    # 禁止删除自己
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能删除管理员自己")

    # 检查用户是否存在
    user = await db_get_user_by_user_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    success = await db_delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="删除失败")

    return success_response(message="用户删除成功", data=None)