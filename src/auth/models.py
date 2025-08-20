import enum
import uuid

from pydantic import EmailStr
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.auth.schemas import UserRead, WorkspaceRead
from src.database import Base, int_pk, uuid_pk


class SystemRole(enum.Enum):
    """System-wide user roles for platform access control."""
    OWNER = "owner"
    SUPERUSER = "superuser"
    FREE_USER = "free_user"
    PAID_USER = "paid_user"
    GUEST = "guest"

class WorkspaceRole(enum.Enum):
    """Workspace-specific roles defining user permissions within an organization."""
    OWNER = "owner"
    MEMBER = "member"
    GUEST = "guest"


class User(Base):
    """User model representing authenticated users with system-level roles."""
    __table_args__ = {"schema": "auth"}
    id: Mapped[uuid_pk]
    email: Mapped[EmailStr] = mapped_column(String(128), nullable=False)
    first_name: Mapped[str] = mapped_column(String(48), nullable=False)
    last_name: Mapped[str] = mapped_column(String(48), nullable=False)
    username: Mapped[str] = mapped_column(String(48), nullable=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean(), default=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=False)
    hashed_password: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        comment="Password hash (bcrypt/argon2)",
    )
    role: Mapped[SystemRole] = mapped_column(
        ENUM(SystemRole, name="system_roles", schema="auth", create_type=False),
        default=SystemRole.FREE_USER,
        nullable=False,
    )
    workspaces_owned: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        foreign_keys="[Workspace.owner_id]",
        back_populates="owner",
        lazy="selectin",
        cascade="none",
        passive_deletes=True,
    )
    workspaces_member: Mapped[list["Workspace"]] = relationship(
        "Workspace",
        secondary="auth.workspace_user",
        back_populates="members",
        lazy="selectin",
    )

    def to_read(self)-> UserRead:
        return UserRead.model_validate(self)


class Workspace(Base):
    """Workspace model representing organizational units that group users."""
    __table_args__ = {"schema": "auth"}
    id: Mapped[int_pk]
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.user.id", ondelete="SET NULL"),
        nullable=False,
        comment="Владелец аккаунта",
    )
    owner: Mapped[User] = relationship(
        User,
        foreign_keys=[owner_id],
        back_populates="workspaces_owned",
        lazy="selectin",
        cascade="none",
        passive_deletes=True,
    )
    members: Mapped[list[User]] = relationship(
        User,
        back_populates="workspaces_member",
        secondary="auth.workspace_user",
        lazy="selectin",
    )

    def to_read(self)-> WorkspaceRead:
        return WorkspaceRead.model_validate(self)

class WorkspaceUser(Base):
    """Association table linking users to workspaces with workspace-specific roles."""
    __table_args__ = {"schema": "auth"}
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("auth.workspace.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("auth.user.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        ENUM(WorkspaceRole, name="workspaces_roles", schema="auth", create_type=False),
        default=WorkspaceRole.MEMBER,
        nullable=False,
    )
