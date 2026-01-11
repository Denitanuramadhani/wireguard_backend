"""
Redis Caching Utilities
Provides caching decorator dan utilities untuk cache management
"""

import json
import functools
from typing import Optional, Callable, Any
from redis import Redis
from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB
from app.logger import logger


# Global Redis client instance
_redis_client: Optional[Redis] = None


def get_redis_client() -> Redis:
    """Get global Redis client instance"""
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5
        )
    return _redis_client


def cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate cache key dari prefix dan arguments
    """
    key_parts = [prefix]
    
    # Add args
    for arg in args:
        if isinstance(arg, (str, int, float, bool)):
            key_parts.append(str(arg))
        elif arg is None:
            key_parts.append("None")
        else:
            key_parts.append(str(hash(str(arg))))
    
    # Add kwargs (sorted untuk consistency)
    for k, v in sorted(kwargs.items()):
        if isinstance(v, (str, int, float, bool)):
            key_parts.append(f"{k}:{v}")
        elif v is None:
            key_parts.append(f"{k}:None")
        else:
            key_parts.append(f"{k}:{hash(str(v))}")
    
    return ":".join(key_parts)


def cached(ttl: int = 300, key_prefix: str = None):
    """
    Decorator untuk cache function results dengan Redis
    ttl: Time to live dalam seconds
    key_prefix: Prefix untuk cache key (default: function name)
    """
    def decorator(func: Callable) -> Callable:
        prefix = key_prefix or f"cache:{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = cache_key(prefix, *args, **kwargs)
            
            try:
                # Try to get from cache
                redis_client = get_redis_client()
                cached_value = redis_client.get(cache_key_str)
                
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {cache_key_str}")
                    return json.loads(cached_value)
                
                # Cache miss, execute function
                logger.debug(f"Cache MISS: {cache_key_str}")
                result = func(*args, **kwargs)
                
                # Store in cache
                try:
                    redis_client.setex(
                        cache_key_str,
                        ttl,
                        json.dumps(result, default=str)
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache result: {e}")
                
                return result
                
            except Exception as e:
                # Redis error, fallback to direct execution
                logger.warning(f"Cache error for {cache_key_str}: {e}, executing function directly")
                return func(*args, **kwargs)
        
        # Add cache invalidation method
        def invalidate(*args, **kwargs):
            """Invalidate cache for specific arguments"""
            cache_key_str = cache_key(prefix, *args, **kwargs)
            try:
                redis_client = get_redis_client()
                redis_client.delete(cache_key_str)
                logger.debug(f"Cache invalidated: {cache_key_str}")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
        
        wrapper.invalidate = invalidate
        wrapper.clear_all = lambda: clear_cache_prefix(prefix)
        
        return wrapper
    
    return decorator


def clear_cache(key: str):
    """Clear specific cache key"""
    try:
        redis_client = get_redis_client()
        redis_client.delete(key)
        logger.debug(f"Cache cleared: {key}")
    except Exception as e:
        logger.warning(f"Failed to clear cache: {e}")


def clear_cache_prefix(prefix: str):
    """Clear all cache keys dengan prefix tertentu"""
    try:
        redis_client = get_redis_client()
        pattern = f"{prefix}:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logger.debug(f"Cleared {len(keys)} cache keys with prefix: {prefix}")
    except Exception as e:
        logger.warning(f"Failed to clear cache prefix: {e}")


def get_cache(key: str) -> Optional[Any]:
    """Get value from cache"""
    try:
        redis_client = get_redis_client()
        value = redis_client.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Failed to get cache: {e}")
        return None


def set_cache(key: str, value: Any, ttl: int = 300):
    """Set value in cache"""
    try:
        redis_client = get_redis_client()
        redis_client.setex(key, ttl, json.dumps(value, default=str))
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"Failed to set cache: {e}")
