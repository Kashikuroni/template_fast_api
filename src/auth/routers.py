from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from src.core.schemas import ResponseSchema
from src.core.services import create_user
from src.database import get_async_session
from src.auth.schemas import WorkspaceCreate, WorkspaceRead, RegisterForm, LoginForm, UserRead, AddWorkspaceMember
from src.auth.models import User, SystemRole, Workspace
from src.auth.utils.passwords import hash_password, verify_password
from src.dependencies import RefreshDep, WorkspacesDep, WorkspaceRepoDep, AuthDep, DBSessionDep, auth
from src.config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    path="/register",
    status_code=status.HTTP_201_CREATED,
    summary="Registration new user",

)
async def register(
    data: RegisterForm,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
) -> ResponseSchema[UUID]:
    """Register a new user and set authentication cookies."""
    user = await create_user(db, data)
    access = auth.create_access_token(uid=str(user.id), fresh=True)
    refresh = auth.create_refresh_token(uid=str(user.id))
    auth.set_access_cookies(access, response)
    auth.set_refresh_cookies(refresh, response)

    return ResponseSchema[UUID](
        data=user.id,
        message="Success registration.",
    )

@router.post(
    path="/login",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Authorization user."
)
async def login(
    data: LoginForm,
    response: Response,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Authenticate user credentials and set login cookies."""
    user = await db.scalar(select(User).where(User.email == data.email))
    if not user or not await verify_password(data.password, str(user.hashed_password)):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized.",
        )
    access = auth.create_access_token(uid=str(user.id), fresh=True)
    refresh = auth.create_refresh_token(uid=str(user.id))
    auth.set_access_cookies(access, response)
    auth.set_refresh_cookies(refresh, response)
    return None

@router.post(
    path="/refresh",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Update access token.",
)
async def refresh_token(
    response: Response,
    payload: RefreshDep,
) -> None:
    """Generate new access and refresh tokens using existing refresh token."""
    new_access = auth.create_access_token(uid=payload.sub, fresh=True)
    refresh = auth.create_refresh_token(uid=str(payload.sub))
    auth.set_access_cookies(new_access, response)
    auth.set_refresh_cookies(refresh, response)
    return None


@router.post(
    path="/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user.",
)
async def logout(response: Response) -> None:
    """Clear authentication cookies and logout user."""
    auth.unset_access_cookies(response)
    auth.unset_refresh_cookies(response)
    return None


@router.get(
    path="/users",
    summary="Get all users.",
    status_code=status.HTTP_200_OK,
)
async def get_user(
    db_session: DBSessionDep,
    payload: AuthDep,
) -> ResponseSchema[UserRead]:
    """Get current authenticated user with workspace information."""
    user_id = UUID(payload.sub)
    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.workspaces_member).options(
                selectinload(Workspace.owner),
            ),
        )
    )

    user: User | None = (await db_session.execute(stmt)).scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized.",
        )

    return ResponseSchema[UserRead](
        data=user.to_read(),
        message="Success retrieving users.",
    )
    
# --------------------------------- Workspace ---------------------------------

@router.post(
    path="/workspaces/create",
    summary="Create new workspace",
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    data: WorkspaceCreate,
    repo: WorkspaceRepoDep
) -> ResponseSchema[str]:
    """Create a new workspace and return its ID."""
    try:
        workspace_id = await repo.create(data=data)
    except Exception:
       raise HTTPException(
           status_code=status.HTTP_400_BAD_REQUEST,
           detail="Failed to create workspace.",
       )

    return ResponseSchema[str](
        data=f"Workspace is created with ID {workspace_id}",
        message="Success creating workspace.",
    )


@router.get(
    path="/workspaces",
    summary="Get all workspaces.",
    status_code=status.HTTP_200_OK,
)
async def get_workspaces(
    repo: WorkspaceRepoDep,
) -> ResponseSchema[Sequence[WorkspaceRead]]:
    """Retrieve all available workspaces."""
    try:
        workspaces: Sequence[Workspace] = await repo.get_all()

        data: list[WorkspaceRead] = []
        for workspace in workspaces:
            data.append(workspace.to_read())

        return ResponseSchema[Sequence[WorkspaceRead]](
            data=data,
            message="Success retrieving workspaces.",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
        )



@router.delete(
    path="/workspaces/{workspace_id}",
    summary="Delete workspace.",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_account(
    workspace_id: int,
    repo: WorkspaceRepoDep,
) -> None:
    """Delete a workspace by ID."""
    is_deleted = await repo.delete(workspace_id)
    if not is_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or already deleted"
        )
    return None

@router.post(
    path="/workspaces/{workspace_id}/add_user",
    summary="Add new user",
    status_code=status.HTTP_201_CREATED,
)
async def add_user_to_workspace(
    workspace_repo: WorkspaceRepoDep,
    workspaces: WorkspacesDep,
    workspace_id: int,
    user: AddWorkspaceMember,
) -> ResponseSchema[str]:
    """Add a user to an existing workspace if authorized."""
    for workspace in workspaces:
        if workspace_id == workspace.id:
            try:
                await workspace_repo.add_user_to_workspace(user.user_id, workspace.id)
                return ResponseSchema(
                    data=f"User {user.user_id} added to workspace {workspace.id}",
                    message="Success adding user to workspace.",
                )
            except Exception as exc:
                if settings.DEBUG:
                    logger.error(f"Failed to add user to workspace {workspace.id}: {exc}")
                raise HTTPException(
                    detail="Failed to add user to workspace.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

    if settings.DEBUG:
        logger.error(
            "An unsuccessful attempt to add a user to a workspace: "
            f"{workspace_id} that the initiator does not have access to"
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Failed to add user to workspace.",
    )

