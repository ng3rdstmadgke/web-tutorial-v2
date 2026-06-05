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


class UserLogin(BaseModel):
    """POST /api/v1/login のリクエストボディ"""
    username: str
    password: str


class UserRead(UserBase):
    """GET レスポンスとして返す User"""
    id: int
    roles: list[RoleRead]

    model_config = ConfigDict(from_attributes=True)

# ===== Item =====

class ItemCreate(BaseModel):
    """POST /api/v1/items/ のリクエストボディ"""
    title: str
    content: str


class ItemUpdate(BaseModel):
    """PATCH /api/v1/items/{item_id} のリクエストボディ"""
    title: str | None = None
    content: str | None = None


class ItemRead(BaseModel):
    """GET レスポンスとして返す Item"""
    id: int
    user_id: int
    title: str
    content: str

    model_config = ConfigDict(from_attributes=True)