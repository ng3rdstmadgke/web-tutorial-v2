
import enum
from typing import Callable

from fastapi import Depends, HTTPException, status

from app import auth
from app.model import RoleType, User


class PermissionType(str, enum.Enum):
    """操作の種類"""
    USER_CREATE = "USER_CREATE"
    USER_READ = "USER_READ"
    USER_UPDATE = "USER_UPDATE"
    USER_DELETE = "USER_DELETE"
    ITEM_CREATE = "ITEM_CREATE"
    ITEM_READ = "ITEM_READ"
    ITEM_UPDATE = "ITEM_UPDATE"
    ITEM_DELETE = "ITEM_DELETE"


# ロールごとに保有する権限を定義
ROLE_PERMISSIONS: dict[RoleType, set[PermissionType]] = {
    RoleType.SYSTEM_ADMIN: {
        PermissionType.USER_CREATE,
        PermissionType.USER_READ,
        PermissionType.USER_UPDATE,
        PermissionType.USER_DELETE,
        PermissionType.ITEM_CREATE,
        PermissionType.ITEM_READ,
        PermissionType.ITEM_UPDATE,
        PermissionType.ITEM_DELETE,
    },
    RoleType.LOCATION_ADMIN: {
        PermissionType.USER_READ,
        PermissionType.USER_UPDATE,
        PermissionType.ITEM_CREATE,
        PermissionType.ITEM_READ,
        PermissionType.ITEM_UPDATE,
        PermissionType.ITEM_DELETE,
    },
    RoleType.LOCATION_OPERATOR: {
        PermissionType.ITEM_CREATE,
        PermissionType.ITEM_READ,
        PermissionType.ITEM_UPDATE,
        PermissionType.ITEM_DELETE,
    },
}


def has_role(user: User, role: RoleType) -> bool:
    """ユーザーが指定されたロールを持っているかを確認する"""
    return role in [r.name for r in user.roles]


def has_permission(user: User, required: list[PermissionType]) -> bool:
    """ユーザーが指定された権限をすべて保有しているかを確認する"""
    user_permissions: set[PermissionType] = set()
    for role in user.roles:
        user_permissions |= ROLE_PERMISSIONS.get(role.name, set())
    return set(required).issubset(user_permissions)


def require_permissions(permissions: list[PermissionType]) -> Callable:
    """指定された権限を持たないユーザーには 403 を返す依存関数を生成する"""

    def _check(current_user: User = Depends(auth.get_current_user)) -> User:
        if not has_permission(current_user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return current_user

    return _check


def check_resource_ownership(
    *,
    owner_id: int,
    current_user: User,
    allow_admin: bool = True,
) -> None:
    """リソースの所有者であることを確認する。

    - owner_id: リソースの所有者のユーザー ID
    - current_user: 現在ログイン中のユーザー
    - allow_admin: True の場合、SYSTEM_ADMIN は所有者チェックをスキップ
    """
    if allow_admin and has_role(current_user, RoleType.SYSTEM_ADMIN):
        return
    if owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )