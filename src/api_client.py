import aiohttp
import asyncio
import logging
from typing import Optional, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class FetchError(Exception):
    """Raised when an HTTP request fails."""

class BaseAPIClient(ABC):
    def __init__(self, max_concurrent_requests: int = 10):
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(headers=self.get_default_headers())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()

    @abstractmethod
    def get_default_headers(self) -> dict[str, Any]:
        """Method to provide default headers, implemented in subclasses."""
        return {}

    async def fetch(
        self,
        url: str,
        body: Optional[dict[str, Any]] = None,
        method: str = "post",
        headers: Optional[dict[str, Any]] = None
    ) -> Any:
        if not self._session:
            raise RuntimeError("Session is not initialized. Use 'async with' context.")

        merged_headers = {**self.get_default_headers(), **(headers or {})}

        req_method = getattr(self._session, method.lower(), None)
        if req_method is None:
            raise ValueError(f"Unsupported HTTP method: {method}")

        async with self._semaphore:
            try:
                async with req_method(url, json=body, headers=merged_headers) as response:
                    if response.status != 200:
                        text = await response.text()
                        msg = f"Request failed ({url=}, {body=}), Response: {text}"
                        logger.error(msg)
                        raise FetchError(msg)
                    return await response.json()

            except aiohttp.ClientError as e:
                msg = f"HTTP client error for request {url=} with body={body}. Details: {str(e)}"
                logger.error(msg)
                raise FetchError(msg)
