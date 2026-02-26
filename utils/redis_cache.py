"""
基于 Redis 的缓存实现，具有 TTL 支持和统计功能
"""
import asyncio
import json
import pickle
from typing import Any, Optional, Dict, List, Union
from functools import wraps
import redis
from redis import Redis
from utils import logger
from config import configer


class CacheStats:
    """缓存统计信息"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self._lock = asyncio.Lock()

    async def increment_hits(self, count: int = 1):
        """增加命中次数"""
        async with self._lock:
            self.hits += count

    async def increment_misses(self, count: int = 1):
        """增加未命中次数"""
        async with self._lock:
            self.misses += count

    async def increment_evictions(self, count: int = 1):
        """增加驱逐次数"""
        async with self._lock:
            self.evictions += count

    async def reset(self):
        """重置统计信息"""
        async with self._lock:
            self.hits = 0
            self.misses = 0
            self.evictions = 0

    @property
    def hit_rate(self) -> float:
        """计算命中率"""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
        }

    def __repr__(self):
        return f"CacheStats(hits={self.hits}, misses={self.misses}, evictions={self.evictions})"


class AsyncRedisCache:
    """
    异步 Redis 缓存实现
    """
    def __init__(self,
                 redis_url: str = configer.redis_url,
                 default_ttl: int = 3600,
                 prefix: str = "notex",
                 encoding: str = "utf-8",
                 enable_stats: bool = True):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.prefix = prefix
        self.enable_stats = enable_stats
        self.encoding = encoding

        # 统计信息
        self.stats = CacheStats() if enable_stats else None

        # 异步 Redis 客户端
        self._redis_client = None

    def _deserialize(self, data: str) -> Any:
        """反序列化数据"""
        try:
            # 先尝试 JSON 解析
            return json.loads(data)
        except json.JSONDecodeError:
            # 失败则尝试 pickle
            return pickle.loads(data.encode(self.encoding))

    def _serialize(self, data: Any) -> str:
        """序列化数据"""
        try:
            # 先尝试 JSON 序列化
            return json.dumps(data)
        except (TypeError, OverflowError):
            # 失败则使用 pickle
            return pickle.dumps(data).decode(self.encoding, errors='ignore')

    async def _get_client(self):
        """获取异步 Redis 客户端"""
        if self._redis_client is None:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(
                self.redis_url,
                decode_responses=True
            )
        return self._redis_client

    def _build_key(self, key: str) -> str:
        """构建完整的缓存键"""
        return f"{self.prefix}:{key}" if self.prefix else key

    async def expire(self, key: str, ttl: int) -> bool:
        """
        设置缓存过期时间
        Args: key: 缓存键
             ttl: 过期时间（秒）
        Returns: bool: 是否设置成功
        """
        redis_client = await self._get_client()
        cache_key = self._build_key(key)
        try:
            result = await redis_client.expire(cache_key, ttl)
            if result:
                logger.debug(f"Cache expire set: {cache_key}, ttl: {ttl}s")
            else:
                logger.debug(f"Cache not found for expire: {cache_key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set expire for cache {key}: {e}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        删除所有匹配模式的缓存键
        Args: pattern: 键模式（支持通配符 * 和 ?）
        Returns: int: 删除的键数量
        """
        # 添加前缀
        redis_client = await self._get_client()
        full_pattern = self._build_key(pattern)

        try:
            # 获取所有匹配的键
            keys = []
            cursor = 0
            while True:
                cursor, matched_keys = await redis_client.scan(
                    cursor=cursor,
                    match=full_pattern,
                    count=1000  # 每次扫描的数量
                )
                keys.extend(matched_keys)
                if cursor == 0:
                    break

            if keys:
                deleted_count = await redis_client.delete(*keys)
                if self.enable_stats:
                    await self.stats.increment_evictions(deleted_count)

                logger.info(f"Invalidated {deleted_count} keys with pattern: {full_pattern}")
                return deleted_count

            return 0

        except Exception as e:
            logger.error(f"Failed to invalidate cache with pattern {pattern}: {e}")
            return 0

    async def clear(self) -> bool:
        """
        清除所有缓存
        Returns: bool: 是否清除成功
        """
        try:
            # 获取所有属于本缓存的键
            pattern = f"{self.prefix}:*" if self.prefix else "*"
            deleted_count = await self.invalidate_pattern(pattern)
            # 重置统计信息
            if self.enable_stats:
                await self.stats.reset()

            logger.info(f"Cache cleared, removed {deleted_count} keys")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        Returns: dict: 统计信息
        """
        if not self.enable_stats:
            return {"enabled": False}

        stats = self.stats.to_dict()
        stats["enabled"] = True

        try:
            # 添加 Redis 信息
            redis_client = await self._get_client()
            info = await redis_client.info("memory")

            stats.update({
                "redis_memory_used": info.get("used_memory", 0),
                "redis_memory_peak": info.get("used_memory_peak", 0),
                "redis_connections": info.get("connected_clients", 0),
            })
        except Exception as e:
            logger.warning(f"Failed to get Redis info: {e}")

        return stats

    async def size(self) -> int:
        """
        获取缓存中的条目数量
        Returns: int: 缓存条目数
        """
        try:
            # 统计所有属于本缓存的键
            pattern = f"{self.prefix}:*" if self.prefix else "*"
            count = 0
            cursor = 0
            redis_client = await self._get_client()
            while True:
                cursor, keys = await redis_client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000
                )
                count += len(keys)

                if cursor == 0:
                    break

            return count

        except Exception as e:
            logger.error(f"Failed to get cache size: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        获取所有缓存键
        Args: pattern: 键模式
        Returns: list: 缓存键列表
        """
        full_pattern = self._build_key(pattern)
        try:
            keys = []
            cursor = 0
            redis_client = await self._get_client()
            while True:
                cursor, matched_keys = await redis_client.scan(
                    cursor=cursor,
                    match=full_pattern,
                    count=1000
                )
                keys.extend(matched_keys)
                if cursor == 0:
                    break
            # 移除前缀
            if self.prefix:
                prefix_len = len(self.prefix) + 1  # +1 for colon
                keys = [key[prefix_len:] for key in keys]

            return keys

        except Exception as e:
            logger.error(f"Failed to get cache keys: {e}")
            return []

    async def get(self, key: str) -> Any:
        """异步获取缓存值"""
        client = await self._get_client()
        cache_key = self._build_key(key)
        try:
            value = await client.get(cache_key)
            if value is None:
                if self.enable_stats:
                    await self.stats.increment_misses()
                return None

            if self.enable_stats:
                await self.stats.increment_hits()

            return self._deserialize(value)
        except Exception as e:
            logger.error(f"Async cache get failed: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """异步设置缓存值"""
        client = await self._get_client()
        cache_key = self._build_key(key)

        if ttl is None:
            ttl = self.default_ttl

        try:
            serialized = self._serialize(value)
            result = await client.setex(cache_key, ttl, serialized)
            return bool(result)
        except Exception as e:
            logger.error(f"Async cache set failed: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """异步删除缓存值"""
        client = await self._get_client()
        cache_key = self._build_key(key)

        try:
            result = await client.delete(cache_key)
            return result > 0
        except Exception as e:
            logger.error(f"Async cache delete failed: {e}")
            return False

    # 其他方法类似实现...

    async def close(self):
        """关闭异步连接"""
        if self._redis_client:
            await self._redis_client.close()

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def __del__(self):
        """析构函数"""
        try:
            self.close()
        except Exception:
            pass  # 忽略析构时的错误


def async_cached(
        cache_instance: Optional[AsyncRedisCache] = None,
        key_prefix: str = "",
        ttl: int = 3600,
):
    """
    异步缓存装饰器
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 构建缓存键
            cache_key = key_prefix or func.__name__

            # 添加参数签名
            if args or kwargs:
                import hashlib
                params_str = str(args) + str(sorted(kwargs.items()))
                param_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{param_hash}"

            # 获取缓存实例
            cache = cache_instance
            if cache is None:
                cache = getattr(func, '_cache_instance', None)

            if cache is None:
                return await func(*args, **kwargs)

            # 尝试从缓存获取
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # 缓存未命中，执行函数
            result = await func(*args, **kwargs)

            # 设置缓存
            if result is not None:
                await cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


