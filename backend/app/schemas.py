from pydantic import BaseModel, ConfigDict

from app.model import RoleType


# ===== Role =====

class RoleRead(BaseModel):
    """レスポンスで返す Role"""
    id: int
    name: RoleType

    # SQLAlchemy のモデル (= ORM オブジェクト) からも model_validate(...) できるようにする
    model_config = ConfigDict(from_attributes=True)


# ===== User =====

class UserBase(BaseModel):
    """User の共通フィールド (Create / Read で共有)"""
    username: str
    avatar_url: str | None = None


class UserCreate(UserBase):
    """POST /api/v1/users/ のリクエストボディ"""
    password: str
    role_ids: list[int]


class UserUpdate(BaseModel):
    """PUT /api/v1/users/{user_id} のリクエストボディ"""
    password: str | None = None
    avatar_url: str | None = None
    role_ids: list[int] | None = None


class UserRead(UserBase):
    """GET レスポンスとして返す User"""
    id: int
    roles: list[RoleRead]

    model_config = ConfigDict(from_attributes=True)