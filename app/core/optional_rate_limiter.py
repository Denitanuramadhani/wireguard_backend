"""
Optional Rate Limiter
Rate limiter yang otomatis skip jika Redis tidak tersedia
"""

from fastapi import Depends
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from app.logger import logger

# Global flag untuk track apakah Redis tersedia (set saat startup)
_redis_available = False

def set_redis_available(available: bool):
    """Set Redis availability status (dipanggil dari main.py startup)"""
    global _redis_available
    _redis_available = available

def check_redis_available() -> bool:
    """Check apakah Redis tersedia"""
    global _redis_available
    # Primary check: use flag yang di-set saat startup
    if _redis_available:
        return True
    
    # Secondary check: verify FastAPILimiter.redis (untuk safety)
    try:
        if hasattr(FastAPILimiter, 'redis') and FastAPILimiter.redis is not None:
            _redis_available = True
            return True
    except Exception:
        pass
    
    return False


def optional_rate_limiter(times: int = 100, seconds: int = 60):
    """
    Optional rate limiter dependency
    Jika Redis tidak tersedia, skip rate limiting (no-op dependency)
    
    Strategy: 
    - Check Redis availability saat dependency dibuat (route registration)
    - Jika Redis available, gunakan RateLimiter dependency
    - Jika Redis tidak available, gunakan no-op dependency
    
    Usage:
        @router.post("/endpoint", dependencies=[optional_rate_limiter(times=10, seconds=60)])
    """
    # Check Redis availability saat dependency dibuat
    # Jika Redis tidak tersedia, return no-op dependency
    if not check_redis_available():
        logger.debug("Redis not available, using no-op rate limiter")
        # Return no-op dependency yang tidak melakukan apa-apa
        def noop():
            return None
        return Depends(noop)
    
    # Redis tersedia, gunakan RateLimiter dependency
    logger.debug(f"Redis available, using rate limiter (times={times}, seconds={seconds})")
    return Depends(RateLimiter(times=times, seconds=seconds))

