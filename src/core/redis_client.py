import redis.asyncio as aioredis
import json
from typing import Optional
from src.config import RadisCacheSettings

class CacheManager:
    def __init__(self):
        self._redis_client: Optional[aioredis.Redis] = None
        self.settings = RadisCacheSettings()
    
    async def _get_redis_client(self) -> aioredis.Redis:
        """Получить Redis клиент (singleton)"""
        if self._redis_client is None:
            self._redis_client = await aioredis.from_url(
                f"redis://{self.settings.REDIS_HOST}:{self.settings.REDIS_PORT}",
                decode_responses=True,
                max_connections=20
            )
        return self._redis_client
    
    async def save_to_cache(self, cache_key: str, data: dict) -> bool:
        """Сохранить данные в кеш"""
        try:
            client = await self._get_redis_client()
            json_data = json.dumps(data, ensure_ascii=False)
            await client.setex(cache_key, self.settings.CACHE_TTL, json_data)
            return True
        except Exception as e:
            print(f"Ошибка сохранения в кеш: {e}")
            return False
    
    async def get_from_cache(self, cache_key: str) -> Optional[dict]:
        """Получить данные из кеша"""
        try:
            client = await self._get_redis_client()
            cached_data: Optional[str] = await client.get(cache_key)
            if cached_data is not None:
                return json.loads(cached_data)
            return None
        except Exception as e:
            print(f"Ошибка получения из кеша: {e}")
            return None
    
    async def clear_cache(self, cache_key: str) -> bool:
        """Очистить кеш"""
        try:
            client = await self._get_redis_client()
            result = await client.delete(cache_key)
            return result > 0
        except Exception as e:
            print(f"Ошибка очистки кеша: {e}")
            return False

    async def exists(self, cache_key: str) -> bool:
        """Проверить существование ключа"""
        try:
            client = await self._get_redis_client()
            return await client.exists(cache_key) > 0
        except Exception:
            return False
    
    async def set_ttl(self, cache_key: str, ttl: int) -> bool:
        """Установить TTL для существующего ключа"""
        try:
            client = await self._get_redis_client()
            return await client.expire(cache_key, ttl)
        except Exception:
            return False
    
    async def get_all_keys(self, pattern: str = "*") -> list:
        """Получить все ключи по шаблону"""
        try:
            client = await self._get_redis_client()
            return await client.keys(pattern)
        except Exception:
            return []
    
    async def close(self):
        """Закрыть соединения"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None

cache_manager = CacheManager()
