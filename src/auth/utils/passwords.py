"""
Парольные хелперы на базе pwdlib 0.2+
argon2id — основной, bcrypt — резервный (для миграции старых хешей).
"""

from typing import Any
from pwdlib import PasswordHash
from argon2.exceptions import (
    InvalidHashError,
    VerifyMismatchError,
)

_pwd = PasswordHash.recommended()

def hash_password(password: str) -> Any:
    """Хешируем пароль → строка вида  $argon2id$…"""
    return _pwd.hash(password)


async def verify_password(plain: str, hashed: str) -> bool:
    """
    Проверяем пароль.
    * True  – совпало;
    * False – не совпало / неизвестная схема.
    Если алгоритм или cost устарели, получим новый хеш и
    сохраняем его в БД асинхронно.
    """
    try:
        verified, new_hash = _pwd.verify_and_update(plain, hashed)
    except InvalidHashError:
        return False
    except VerifyMismatchError:
        return False

    if verified and new_hash:
        # «тихое» обновление cost-параметров
        from src.database import async_session_maker
        from src.auth.models import User
        import sqlalchemy as sa
        import asyncio

        async def _store():
            async with async_session_maker() as ses:
                await ses.execute(
                    sa.update(User)
                      .where(User.hashed_password == hashed)
                      .values(hashed_password=new_hash)
                )
                await ses.commit()

        asyncio.create_task(_store())

    return verified
