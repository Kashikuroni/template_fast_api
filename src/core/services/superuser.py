from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from src.auth.models import User, SystemRole
from src.auth.schemas import RegisterForm
from src.auth.utils.passwords import hash_password
from src.config import super_user_settings, settings
from src.database import async_session_maker


async def create_user(db_session: AsyncSession, data: RegisterForm) -> User | None:
    exists = await db_session.scalar(select(User).where(User.email == data.email))
    if exists:
        if settings.DEBUG:
            logger.info(f"User with email {data.email} already exists")
            return None

    user = User(
        email=data.email,
        first_name=data.first_name,
        last_name=data.last_name,
        username=data.username,
        hashed_password=hash_password(data.password),
        is_active=True,
        role=SystemRole.OWNER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


async def create_superuser():
    async with async_session_maker() as db_session:
        data = RegisterForm(
            email=super_user_settings.SUPERUSER_EMAIL,
            password=super_user_settings.SUPERUSER_PASSWORD,
            firstName=super_user_settings.SUPERUSER_FIRSTNAME,
            lastName=super_user_settings.SUPERUSER_LASTNAME,
            username=super_user_settings.SUPERUSER_USERNAME,
        )
        await create_user(db_session, data)