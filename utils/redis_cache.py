"""
基于 Redis 的缓存实现，具有 TTL 支持和统计功能
"""

import json
import pickle
import time
import asyncio
import threading
import logging
from typing import Any, Optional, Dict, List, Union
from datetime import datetime, timedelta
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
        self._lock = threading.RLock()

    def increment_hits(self, count: int = 1):
        """增加命中次数"""
        with self._lock:
            self.hits += count

    def increment_misses(self, count: int = 1):
        """增加未命中次数"""
        with self._lock:
            self.misses += count

    def increment_evictions(self, count: int = 1):
        """增加驱逐次数"""
        with self._lock:
            self.evictions += count

    def reset(self):
        """重置统计信息"""
        with self._lock:
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


class RedisCache:
    """
    基于 Redis 的缓存实现，具有 TTL 支持和统计功能

    功能特点：
    1. 支持 TTL（过期时间）
    2. 自动清理过期键
    3. 缓存统计（命中率、未命中率等）
    4. 支持模式匹配删除
    5. 线程安全
    """

    def __init__(
            self,
            redis_url: str = configer.redis_url,
            default_ttl: int = 3600,  # 默认 TTL（秒）
            cleanup_interval: int = 60,  # 清理间隔（秒）
            prefix: str = "notex",
            encoding: str = "utf-8",
            enable_stats: bool = True,
    ):
        """
        初始化 Redis 缓存

        Args:
            redis_url: Redis 连接 URL
            default_ttl: 默认 TTL（秒）
            cleanup_interval: 清理过期键的间隔（秒）
            prefix: 缓存键前缀
            encoding: 编码格式
            enable_stats: 是否启用统计
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.prefix = prefix
        self.encoding = encoding
        self.enable_stats = enable_stats

        # Redis 连接
        self._redis_client: Optional[Redis] = None

        # 统计信息
        self.stats = CacheStats() if enable_stats else None

        # 清理线程
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()

        # 连接 Redis
        self._connect()

        # 启动清理线程
        if cleanup_interval > 0:
            self._start_cleanup_thread()

    def _connect(self):
        """连接到 Redis"""
        try:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding=self.encoding,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )

            # 测试连接
            self._redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _ensure_connection(self):
        """确保 Redis 连接可用"""
        if self._redis_client is None:
            self._connect()

        try:
            self._redis_client.ping()
        except Exception:
            logger.warning("Redis connection lost, reconnecting...")
            self._connect()

    def _build_key(self, key: str) -> str:
        """构建完整的缓存键"""
        return f"{self.prefix}:{key}" if self.prefix else key

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

    def get(self, key: str) -> Any:
        """
        从缓存中获取值
        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或已过期则返回 None
        """
        self._ensure_connection()

        cache_key = self._build_key(key)

        try:
            # 获取值（Redis 会自动处理过期）
            value = self._redis_client.get(cache_key)

            if value is None:
                # 缓存未命中
                if self.enable_stats:
                    self.stats.increment_misses()
                logger.debug(f"Cache miss: {cache_key}")
                return None

            # 缓存命中
            if self.enable_stats:
                self.stats.increment_hits()
            logger.debug(f"Cache hit: {cache_key}")

            # 反序列化并返回
            return self._deserialize(value)

        except Exception as e:
            logger.error(f"Failed to get cache {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            bool: 是否设置成功
        """
        self._ensure_connection()

        cache_key = self._build_key(key)

        if ttl is None:
            ttl = self.default_ttl

        try:
            # 序列化值
            serialized = self._serialize(value)

            # 设置缓存（带 TTL）
            result = self._redis_client.setex(cache_key, ttl, serialized)

            if result:
                logger.debug(f"Cache set: {cache_key}, ttl: {ttl}s")
            else:
                logger.warning(f"Failed to set cache: {cache_key}")

            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set cache {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        删除缓存值

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        self._ensure_connection()

        cache_key = self._build_key(key)

        try:
            result = self._redis_client.delete(cache_key)
            deleted = result > 0

            if deleted:
                logger.debug(f"Cache deleted: {cache_key}")
            else:
                logger.debug(f"Cache not found for deletion: {cache_key}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete cache {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            bool: 是否存在
        """
        self._ensure_connection()

        cache_key = self._build_key(key)

        try:
            return self._redis_client.exists(cache_key) > 0
        except Exception as e:
            logger.error(f"Failed to check cache {key}: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """
        设置缓存过期时间

        Args:
            key: 缓存键
            ttl: 过期时间（秒）

        Returns:
            bool: 是否设置成功
        """
        self._ensure_connection()

        cache_key = self._build_key(key)

        try:
            result = self._redis_client.expire(cache_key, ttl)

            if result:
                logger.debug(f"Cache expire set: {cache_key}, ttl: {ttl}s")
            else:
                logger.debug(f"Cache not found for expire: {cache_key}")

            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set expire for cache {key}: {e}")
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        删除所有匹配模式的缓存键

        Args:
            pattern: 键模式（支持通配符 * 和 ?）

        Returns:
            int: 删除的键数量
        """
        self._ensure_connection()

        # 添加前缀
        full_pattern = self._build_key(pattern)

        try:
            # 获取所有匹配的键
            keys = []
            cursor = 0

            while True:
                cursor, matched_keys = self._redis_client.scan(
                    cursor=cursor,
                    match=full_pattern,
                    count=1000  # 每次扫描的数量
                )
                keys.extend(matched_keys)

                if cursor == 0:
                    break

            # 批量删除
            if keys:
                deleted_count = self._redis_client.delete(*keys)

                if self.enable_stats:
                    self.stats.increment_evictions(deleted_count)

                logger.info(f"Invalidated {deleted_count} keys with pattern: {full_pattern}")
                return deleted_count

            return 0

        except Exception as e:
            logger.error(f"Failed to invalidate cache with pattern {pattern}: {e}")
            return 0

    def clear(self) -> bool:
        """
        清除所有缓存

        Returns:
            bool: 是否清除成功
        """
        self._ensure_connection()

        try:
            # 获取所有属于本缓存的键
            pattern = f"{self.prefix}:*" if self.prefix else "*"
            deleted_count = self.invalidate_pattern(pattern)

            # 重置统计信息
            if self.enable_stats:
                self.stats.reset()

            logger.info(f"Cache cleared, removed {deleted_count} keys")
            return True

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            dict: 统计信息
        """
        if not self.enable_stats:
            return {"enabled": False}

        stats = self.stats.to_dict()
        stats["enabled"] = True

        try:
            # 添加 Redis 信息
            self._ensure_connection()
            info = self._redis_client.info("memory")

            stats.update({
                "redis_memory_used": info.get("used_memory", 0),
                "redis_memory_peak": info.get("used_memory_peak", 0),
                "redis_connections": info.get("connected_clients", 0),
            })
        except Exception as e:
            logger.warning(f"Failed to get Redis info: {e}")

        return stats

    def size(self) -> int:
        """
        获取缓存中的条目数量

        Returns:
            int: 缓存条目数
        """
        self._ensure_connection()

        try:
            # 统计所有属于本缓存的键
            pattern = f"{self.prefix}:*" if self.prefix else "*"
            count = 0

            cursor = 0
            while True:
                cursor, keys = self._redis_client.scan(
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

    def keys(self, pattern: str = "*") -> List[str]:
        """
        获取所有缓存键

        Args:
            pattern: 键模式

        Returns:
            list: 缓存键列表
        """
        self._ensure_connection()

        full_pattern = self._build_key(pattern)

        try:
            keys = []
            cursor = 0

            while True:
                cursor, matched_keys = self._redis_client.scan(
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

    def _cleanup_expired(self):
        """清理过期键（Redis 会自动处理，这里只是日志记录）"""
        try:
            self._ensure_connection()

            # Redis 会自动删除过期键，这里我们只记录日志
            logger.debug("Redis automatic expiration cleanup running")

        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")

    def _cleanup_loop(self):
        """清理循环"""
        logger.info(f"Cache cleanup thread started, interval: {self.cleanup_interval}s")

        while not self._stop_cleanup.wait(self.cleanup_interval):
            try:
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

        logger.info("Cache cleanup thread stopped")

    def _start_cleanup_thread(self):
        """启动清理线程"""
        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="CacheCleanup"
        )
        self._cleanup_thread.start()

    def stop_cleanup(self):
        """停止清理线程"""
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
            self._cleanup_thread = None
            logger.info("Cache cleanup stopped")

    def close(self):
        """关闭连接并停止清理线程"""
        self.stop_cleanup()

        if self._redis_client:
            try:
                self._redis_client.close()
                self._redis_client = None
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Failed to close Redis connection: {e}")

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


# 异步版本
class AsyncRedisCache:
    """
    异步 Redis 缓存实现
    """

    def __init__(
            self,
            redis_url: str = configer.redis_url,
            default_ttl: int = 3600,
            prefix: str = "notex",
            enable_stats: bool = True,
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.prefix = prefix
        self.enable_stats = enable_stats

        # 统计信息
        self.stats = CacheStats() if enable_stats else None

        # 异步 Redis 客户端
        self._redis_client = None

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

    async def get(self, key: str) -> Any:
        """异步获取缓存值"""
        client = await self._get_client()
        cache_key = self._build_key(key)

        try:
            value = await client.get(cache_key)

            if value is None:
                if self.enable_stats:
                    self.stats.increment_misses()
                return None

            if self.enable_stats:
                self.stats.increment_hits()

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


# 缓存装饰器
def cached(
        cache_instance: Optional[RedisCache] = None,
        key_prefix: str = "",
        ttl: int = 3600,
        ignore_args: List[int] = None,
        ignore_kwargs: List[str] = None,
):
    """
    缓存装饰器

    Args:
        cache_instance: 缓存实例
        key_prefix: 键前缀
        ttl: 缓存时间（秒）
        ignore_args: 要忽略的参数索引列表
        ignore_kwargs: 要忽略的关键字参数列表
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 构建缓存键
            cache_key = key_prefix or func.__name__

            # 添加参数签名
            if args or kwargs:
                import hashlib

                # 过滤忽略的参数
                filtered_args = list(args)
                if ignore_args:
                    for idx in sorted(ignore_args, reverse=True):
                        if idx < len(filtered_args):
                            filtered_args.pop(idx)

                filtered_kwargs = dict(kwargs)
                if ignore_kwargs:
                    for key in ignore_kwargs:
                        filtered_kwargs.pop(key, None)

                # 生成参数哈希
                params_str = str(filtered_args) + str(sorted(filtered_kwargs.items()))
                param_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
                cache_key = f"{cache_key}:{param_hash}"

            # 获取缓存实例
            cache = cache_instance
            if cache is None:
                # 如果没有提供缓存实例，尝试使用全局实例
                cache = getattr(func, '_cache_instance', None)

            if cache is None:
                # 没有缓存，直接执行函数
                return func(*args, **kwargs)

            # 尝试从缓存获取
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for function {func.__name__}")
                return cached_result

            # 缓存未命中，执行函数
            result = func(*args, **kwargs)

            # 设置缓存
            if result is not None:
                cache.set(cache_key, result, ttl)
                logger.debug(f"Cache set for function {func.__name__}")

            return result

        return wrapper

    return decorator


# 异步缓存装饰器
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


