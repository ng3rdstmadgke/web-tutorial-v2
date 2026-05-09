from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import auth
from app.model import Role, User
from app.schemas import UserCreate, UserRead, UserUpdate
from app.session import get_session

router = APIRouter()


@router.post("/users/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    session: Session = Depends(get_session),
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
    return user

@router.get("/users/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    session: Session = Depends(get_session),
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