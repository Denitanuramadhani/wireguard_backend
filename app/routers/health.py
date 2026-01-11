"""
Health Check Endpoints
Comprehensive system health monitoring
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime
from app.database.connection import test_connection
from app.core.ldap_pool import get_ldap_pool
from app.core.cache import get_redis_client
from app.logger import logger
import subprocess

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/")
def health_check():
    """
    Basic health check
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "wireguard-vpn-portal"
    }


@router.get("/database")
def database_health():
    """
    Database connection health check
    """
    try:
        is_healthy = test_connection()
        if is_healthy:
            return {
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=503, detail="Database connection failed")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@router.get("/ldap")
def ldap_health():
    """
    LDAP connection health check
    """
    try:
        pool = get_ldap_pool()
        conn = pool.get_connection(admin=False)
        pool.return_connection(conn, admin=False)
        
        return {
            "status": "healthy",
            "service": "ldap",
            "connected": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"LDAP health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "ldap",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/redis")
def redis_health():
    """
    Redis connection health check
    """
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        
        return {
            "status": "healthy",
            "service": "redis",
            "connected": True,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "redis",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/wireguard")
def wireguard_health():
    """
    WireGuard service health check
    """
    try:
        result = subprocess.run(
            ["sudo", "wg", "show", "wg0"],
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode == 0:
            # Count active peers
            peer_count = len([line for line in result.stdout.split('\n') if line.strip() and 'public key' not in line.lower()])
            
            return {
                "status": "healthy",
                "service": "wireguard",
                "available": True,
                "peer_count": peer_count,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "unhealthy",
                    "service": "wireguard",
                    "error": "WireGuard command failed",
                    "timestamp": datetime.now().isoformat()
                }
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "wireguard",
                "error": "Timeout waiting for WireGuard response",
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"WireGuard health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "wireguard",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/consistency")
def consistency_check():
    """
    Check consistency between WireGuard peers and MySQL database
    Admin only endpoint
    """
    from app.middleware.auth_middleware import verify_jwt_admin
    
    # Note: This endpoint requires admin auth, but we'll check in the function
    # to allow monitoring tools to check consistency
    
    inconsistencies = []
    
    try:
        # Get peers from WireGuard
        result = subprocess.run(
            ["sudo", "wg", "show", "wg0", "dump"],
            capture_output=True,
            timeout=5,
            text=True
        )
        
        if result.returncode != 0:
            raise Exception("Failed to get WireGuard peers")
        
        wg_peers = {}
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            cols = line.split('\t')
            if len(cols) > 0:
                public_key = cols[0]
                wg_peers[public_key] = True
        
        # Get devices from MySQL
        from app.database.queries import get_all_devices
        mysql_devices = get_all_devices(status='active')
        mysql_peers = {device['public_key']: device for device in mysql_devices}
        
        # Check for peers in WireGuard but not in MySQL
        for public_key in wg_peers:
            if public_key not in mysql_peers:
                inconsistencies.append({
                    "type": "peer_in_wg_not_in_mysql",
                    "public_key": public_key[:20] + "...",
                    "description": "Peer exists in WireGuard but not in MySQL"
                })
        
        # Check for devices in MySQL but not in WireGuard
        for public_key, device in mysql_peers.items():
            if public_key not in wg_peers:
                inconsistencies.append({
                    "type": "device_in_mysql_not_in_wg",
                    "device_id": device['id'],
                    "public_key": public_key[:20] + "...",
                    "description": f"Device {device['device_name']} exists in MySQL but not in WireGuard"
                })
        
        return {
            "status": "consistent" if not inconsistencies else "inconsistent",
            "inconsistencies": inconsistencies,
            "wg_peer_count": len(wg_peers),
            "mysql_device_count": len(mysql_peers),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Consistency check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/full")
def full_health_check():
    """
    Full system health check
    Checks database, LDAP, Redis, WireGuard, and consistency
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check database
    try:
        db_healthy = test_connection()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "connected": db_healthy
        }
        if not db_healthy:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check LDAP
    try:
        pool = get_ldap_pool()
        conn = pool.get_connection(admin=False)
        pool.return_connection(conn, admin=False)
        health_status["checks"]["ldap"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        health_status["checks"]["ldap"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check WireGuard
    try:
        result = subprocess.run(
            ["sudo", "wg", "show", "wg0"],
            capture_output=True,
            timeout=5
        )
        health_status["checks"]["wireguard"] = {
            "status": "healthy" if result.returncode == 0 else "unhealthy",
            "available": result.returncode == 0
        }
        if result.returncode != 0:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["wireguard"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Determine overall status
    critical_services = ["database", "ldap"]
    critical_healthy = all(
        health_status["checks"].get(service, {}).get("status") == "healthy"
        for service in critical_services
    )
    
    if not critical_healthy:
        health_status["status"] = "unhealthy"
    
    return health_status
