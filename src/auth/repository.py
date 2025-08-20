"""
Workspace repository implementation for CRUD operations using SQLAlchemy.

This module provides a concrete repository for the `Workspace` model,
supporting asynchronous Create, Read, Update, and Delete (CRUD) operations.
The repository leverages SQLAlchemy Core statements for all database interactions.
"""
from typing import Optional, Sequence
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import or_, select, update, delete, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement
from src.auth.models import Workspace, WorkspaceUser, WorkspaceRole, User
from src.auth.schemas import WorkspaceCreate, WorkspaceUpdate


class WorkspaceRepository:
    """Repository for workspace CRUD operations with user-based access control."""
    
    def __init__(self, db_session: AsyncSession, user_id: str):
        """Initialize repository with database session and user context."""
        self.db_session = db_session
        self.user_id = user_id

    @property
    def workspace_access_filter(self) -> ColumnElement[bool]:
        """SQLAlchemy filter ensuring user can only access workspaces they own or are members of."""
        return or_(
            Workspace.owner_id == self.user_id,
            Workspace.members.any(id=self.user_id)
        )


    async def create(self, data: WorkspaceCreate) -> int:
        """Create a new workspace and add the owner as a member."""
        workspace_stmt = (
            insert(Workspace)
            .values(
                **data.model_dump(),
                owner_id=self.user_id
            )
            .returning(Workspace.id)
        )
        workspace_result = await self.db_session.execute(workspace_stmt)
        workspace_id = workspace_result.scalar_one()

        workspace_user_stmt = (
            insert(WorkspaceUser)
            .values(
                workspace_id=workspace_id,
                user_id=self.user_id,
                role=WorkspaceRole.OWNER
            )
        )
        await self.db_session.execute(workspace_user_stmt)

        await self.db_session.commit()
        return workspace_id

    async def get_by_id(self, obj_id: int) -> Optional[Workspace]:
        """Retrieve a workspace by ID if user has access."""
        stmt = (
            select(Workspace)
            .options(selectinload(Workspace.members), selectinload(Workspace.owner))
            .where(
                Workspace.id == obj_id,
                self.workspace_access_filter
            )
        )
        result = await self.db_session.execute(stmt)
        return result.scalars().first()

    async def get_by_id_or_404(self, obj_id: int) -> Workspace:
        """Retrieve a workspace by ID or raise 404 if not found/no access."""
        account = await self.get_by_id(obj_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied"
            )
        return account

    async def get_list(self, limit: int = 100, offset: int = 0) -> Sequence[Workspace]:
        """Get paginated list of accessible workspaces."""
        stmt = select(Workspace).limit(limit).offset(offset).where(self.workspace_access_filter)
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def get_all(self) -> Sequence[Workspace]:
        """Get all accessible workspaces for the current user."""
        stmt = (
            select(Workspace)
            .where(self.workspace_access_filter)
        )
        result = await self.db_session.execute(stmt)
        return result.scalars().all()

    async def update(self, obj_id: int, data: WorkspaceUpdate) -> Optional[Workspace]:
        """Update a workspace if user has access."""
        stmt = (
            update(Workspace)
            .where(Workspace.id == obj_id, self.workspace_access_filter)
            .values(**data.model_dump(exclude_unset=True))
            .returning(Workspace)
        )
        result = await self.db_session.execute(stmt)
        await self.db_session.commit()
        updated = result.fetchone()
        if updated:
            return await self.get_by_id(obj_id)
        return None

    async def delete(self, obj_id: int) -> bool:
        """Delete a workspace and all related memberships if user has access."""
        workspace_user_stmt = delete(WorkspaceUser).where(WorkspaceUser.workspace_id == obj_id)
        await self.db_session.execute(workspace_user_stmt)
        
        workspace_stmt = delete(Workspace).where(Workspace.id == obj_id, self.workspace_access_filter)
        result = await self.db_session.execute(workspace_stmt)
        
        await self.db_session.commit()
        return result.rowcount > 0

    async def add_user_to_workspace(self, add_user_id: UUID, workspace_id: int) -> bool:
        """Add a user to a workspace with validation and access control."""
        user_check_stmt = select(User).where(User.id == add_user_id)
        user_exists = await self.db_session.scalar(user_check_stmt)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        workspace_check_stmt = (
            select(Workspace)
            .where(Workspace.id == workspace_id, self.workspace_access_filter)
        )
        workspace_exists = await self.db_session.scalar(workspace_check_stmt)
        if not workspace_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found or access denied."
            )

        existing_membership_stmt = (
            select(WorkspaceUser)
            .where(
                WorkspaceUser.workspace_id == workspace_id,
                WorkspaceUser.user_id == add_user_id
            )
        )
        existing_membership = await self.db_session.scalar(existing_membership_stmt)
        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a member of this workspace."
            )

        stmt = (
            insert(WorkspaceUser)
            .values(
                workspace_id=workspace_id, 
                user_id=add_user_id,
                role=WorkspaceRole.MEMBER
            )
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()
        return True



