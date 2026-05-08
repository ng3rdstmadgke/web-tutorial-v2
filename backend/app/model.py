import enum
from datetime import datetime, timezone
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class RoleType(str, enum.Enum):
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    LOCATION_ADMIN = "LOCATION_ADMIN"
    LOCATION_OPERATOR = "LOCATION_OPERATOR"


def now_utc() -> datetime:
    """タイムゾーン付きの現在時刻 (UTC) を返す"""
    return datetime.now(timezone.utc)


class User(Base):
    """users テーブル"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text, default=None)  # ← 追加
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    items: Mapped[list["Item"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"


class Item(Base):
    """items テーブル"""
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(String(128))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, user_id={self.user_id}, title={self.title})>"


class Role(Base):
    """roles テーブル"""
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[RoleType] = mapped_column(
        Enum(RoleType, name="role_type"),
        unique=True,
        index=True,
    )
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    users: Mapped[list["User"]] = relationship(
        secondary="user_roles",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class UserRole(Base):
    """users と roles の中間テーブル"""
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="unique_idx_userid_roleid"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"))
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)