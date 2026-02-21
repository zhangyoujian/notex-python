from typing import Optional

from pydantic import BaseModel, Field, ConfigDict



class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str


class UpdateRequest(BaseModel):
    email: str
    username: Optional[str]
    password: Optional[str]


# user_info 对应的类：基础类 + Info 类（id、用户名）
class UserInfoBase(BaseModel):
    """
    用户信息基础数据模型
    """
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")


class UserInfoResponse(UserInfoBase):
    username: str
    email: str

    # 模型类配置
    model_config = ConfigDict(
        from_attributes=True  # 允许从 ORM 对象属性中取值
    )


# data 数据类型
class UserAuthResponse(BaseModel):
    token: str
    user: UserInfoResponse = Field(..., alias="userInfo")

    # 模型类配置
    model_config = ConfigDict(
        populate_by_name=True,  # alias / 字段名兼容
        from_attributes=True  # 允许从 ORM 对象属性中取值
    )

