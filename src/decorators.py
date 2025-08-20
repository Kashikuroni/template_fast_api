import functools
from typing import Optional

from loguru import logger


def safe_call_async(debug: Optional[bool] = True):
    """
    A decorator for wrapping a function in try except.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if debug:
                    logger.error(f"Error when calling the function {func.__name__}: {e}")
                return None
        return wrapper
    return decorator
