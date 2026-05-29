import structlog

logger = structlog.get_logger()

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import env
from app import auth
from app.model import Role, RoleType, User, Item
from app.schemas import UserCreate, UserRead, UserUpdate, UserLogin, ItemCreate, ItemRead, ItemUpdate
from app.session import get_session
from app.permissions import PermissionType, require_permissions, check_resource_ownership, has_role

router = APIRouter()


@router.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_CREATE])),
) -> User:
    # ユーザー名の重複チェック
    existing = session.execute(
        select(User).where(User.username == data.username)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{data.username}' is already taken",
        )

    # role_ids から Role を取得 (存在しない id があれば 404)
    roles: list[Role] = []
    for role_id in data.role_ids:
        role = session.execute(
            select(Role).where(Role.id == role_id)
        ).scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role not found (id={role_id})",
            )
        roles.append(role)

    user = User(
        username=data.username,
        hashed_password=auth.hash_password(data.password),
        avatar_url=data.avatar_url,
        roles=roles,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    # ビジネスイベントのログ
    logger.info("user_created", user_id=user.id, username=user.username)
    return user

@router.get("/users/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_READ])),
) -> User:
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found (id={user_id})",
        )
    return user

@router.get("/users/", response_model=list[UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_READ])),
) -> list[User]:
    users = session.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    ).scalars().all()
    return list(users)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: "UserUpdate",
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_UPDATE])),
) -> User:
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found (id={user_id})",
        )

    if data.password is not None:
        user.hashed_password = auth.hash_password(data.password)
    if data.avatar_url is not None:
        user.avatar_url = data.avatar_url
    if data.role_ids is not None:
        roles: list[Role] = []
        for role_id in data.role_ids:
            role = session.execute(
                select(Role).where(Role.id == role_id)
            ).scalar_one_or_none()
            if role is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role not found (id={role_id})",
                )
            roles.append(role)
        user.roles = roles

    session.add(user)
    session.commit()
    session.refresh(user)
    return user

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    _: User = Depends(require_permissions([PermissionType.USER_DELETE])),
) -> None:
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User not found (id={user_id})",
        )
    session.delete(user)
    session.commit()

@router.post("/login")
def login(
    response: Response,
    data: UserLogin,
    session: Session = Depends(get_session),
):
    """ユーザー名とパスワードでログインし、JWT トークンを発行する"""
    user = session.execute(
        select(User).where(User.username == data.username)
    ).scalar_one_or_none()

    if user is None or not auth.verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # JWT を生成
    token = auth.create_access_token(user.username)

    # Cookie にセット (ブラウザ用)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,       # JS からアクセス不可 (XSS 対策)
        samesite="lax",     # CSRF 対策 (異なるサイトからの POST ではCookieを送らない)
        secure=env.cookie_secure,  # 本番は True (HTTPS でのみCookieを送信する)
        max_age=env.token_expire_minutes * 60,  # 秒単位
    )

    # レスポンスボディにも返す (API クライアント / curl 用)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout(response: Response):
    """Cookie を削除してログアウトする"""
    response.delete_cookie(key="access_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserRead)
def read_me(
    current_user: User = Depends(auth.get_current_user),
) -> User:
    """ログイン中のユーザー自身の情報を返す"""
    return current_user


# === Item CRUD ===

@router.post("/items/", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
def create_item(
    data: ItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_CREATE])),
) -> Item:
    """ログインユーザーのアイテムを作成する"""
    item = Item(title=data.title, content=data.content)
    current_user.items.append(item)
    session.add(current_user)
    session.commit()
    session.refresh(item)
    return item


@router.get("/items/", response_model=list[ItemRead])
def read_items(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_READ])),
) -> list[Item]:
    """ログインユーザーのアイテム一覧を取得する。
    SYSTEM_ADMIN は全ユーザーのアイテムを取得できる。
    """
    query = select(Item)
    if not has_role(current_user, RoleType.SYSTEM_ADMIN):
        # 一般ユーザーは自分のアイテムのみ
        query = query.where(Item.user_id == current_user.id)
    items = session.execute(
        query.offset(skip).limit(limit).order_by(Item.id)
    ).scalars().all()
    return list(items)


@router.get("/items/{item_id}", response_model=ItemRead)
def read_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_READ])),
) -> Item:
    """アイテムを取得する。自分のアイテムか SYSTEM_ADMIN のみ"""
    item = session.execute(
        select(Item).where(Item.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    check_resource_ownership(owner_id=item.user_id, current_user=current_user)
    return item


@router.patch("/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    data: ItemUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_UPDATE])),
) -> Item:
    """アイテムを更新する。自分のアイテムか SYSTEM_ADMIN のみ"""
    item = session.execute(
        select(Item).where(Item.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    check_resource_ownership(owner_id=item.user_id, current_user=current_user)

    if data.title is not None:
        item.title = data.title
    if data.content is not None:
        item.content = data.content
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permissions([PermissionType.ITEM_DELETE])),
) -> None:
    """アイテムを削除する。自分のアイテムか SYSTEM_ADMIN のみ"""
    item = session.execute(
        select(Item).where(Item.id == item_id)
    ).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    check_resource_ownership(owner_id=item.user_id, current_user=current_user)
    session.delete(item)
    session.commit()

@router.get("/test-error")
def test_error():
    raise RuntimeError("This is a test error")