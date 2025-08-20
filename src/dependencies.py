from typing import Annotated

from authx import AuthX, TokenPayload
from sqlalchemy import Sequence

from src.config import authx_config
from src.auth.models import User
from src.auth.repository import WorkspaceRepository

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from src.auth.models import Workspace
from src.database import get_async_session

auth = AuthX(
    config=authx_config,
    model=User,
)

DBSessionDep: type[AsyncSession] = Annotated[AsyncSession, Depends(get_async_session)]
AuthDep: type[TokenPayload] = Annotated[TokenPayload, Depends(auth.access_token_required)]
RefreshDep: type[TokenPayload] = Annotated[TokenPayload, Depends(auth.refresh_token_required)]

def get_account_repository(
    db_session: DBSessionDep,
    payload: AuthDep
) -> WorkspaceRepository:
    return WorkspaceRepository(db_session, payload.sub)

WorkspaceRepoDep: type[WorkspaceRepository] = Annotated[WorkspaceRepository, Depends(get_account_repository)]

async def get_workspaces_by_user(
    payload: AuthDep,
    db_session: DBSessionDep,
) -> Sequence[Workspace]:
    """
    Получить workspace, к которому пользователь имеет доступ (owner или member).
    Использует user_id из payload.sub.
    """
    user_id = UUID(payload.sub)

    stmt = (
        select(Workspace)
        .options(selectinload(Workspace.members))
        .where(
            (Workspace.owner_id == user_id) |
            (Workspace.members.any(id=user_id))
        )
    )
    result = await db_session.execute(stmt)
    workspaces = result.scalars()
    if not workspaces:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found or not accessible for current user",
        )
    return workspaces

WorkspacesDep: type[list[Workspace]] = Annotated[Sequence[Workspace], Depends(get_workspaces_by_user)]

