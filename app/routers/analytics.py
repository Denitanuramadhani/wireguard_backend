"""
Analytics Endpoints
Traffic analytics dan statistics
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt, verify_jwt_admin
from app.database.queries import get_traffic_logs, get_traffic_summary
from app.services.device_service import get_device_info
from app.logger import logger

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/traffic", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
def get_traffic_analytics(
    request: Request,
    device_id: int = Query(None, description="Filter by device ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (max 168 = 7 days)"),
    limit: int = Query(100, ge=1, le=1000, description="Max number of log entries")
):
    """
    Get traffic analytics data untuk grafik
    User bisa lihat traffic device sendiri
    Admin bisa lihat semua traffic
    """
    username = verify_jwt(request)
    is_admin = False
    
    # Check if admin
    try:
        verify_jwt_admin(request)
        is_admin = True
    except:
        pass
    
    # Get device info untuk verify ownership (jika bukan admin)
    if device_id and not is_admin:
        device = get_device_info(device_id, username)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found or access denied")
    
    start_time = datetime.now() - timedelta(hours=hours)
    
    # Get traffic logs
    logs = get_traffic_logs(
        device_id=device_id,
        ldap_uid=username if not is_admin else None,
        start_time=start_time,
        limit=limit
    )
    
    # Format untuk grafik (time series data)
    chart_data = []
    for log in logs:
        chart_data.append({
            "timestamp": log['recorded_at'].isoformat() if isinstance(log['recorded_at'], datetime) else str(log['recorded_at']),
            "transfer_rx": log['transfer_rx'],
            "transfer_tx": log['transfer_tx'],
            "transfer_total": log['transfer_total']
        })
    
    # Get summary
    summary = get_traffic_summary(
        device_id=device_id,
        ldap_uid=username if not is_admin else None,
        hours=hours
    )
    
    return {
        "status": "ok",
        "device_id": device_id,
        "hours": hours,
        "summary": summary,
        "data": chart_data,
        "count": len(chart_data)
    }


@router.get("/device/{device_id}", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def get_device_analytics(
    device_id: int,
    request: Request,
    hours: int = Query(24, ge=1, le=168)
):
    """
    Get analytics untuk specific device
    """
    username = verify_jwt(request)
    
    # Verify device ownership
    device = get_device_info(device_id, username)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found or access denied")
    
    # Get traffic logs
    start_time = datetime.now() - timedelta(hours=hours)
    logs = get_traffic_logs(
        device_id=device_id,
        start_time=start_time,
        limit=1000
    )
    
    # Get summary
    summary = get_traffic_summary(device_id=device_id, hours=hours)
    
    return {
        "status": "ok",
        "device": {
            "device_id": device_id,
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip']
        },
        "summary": summary,
        "logs": [
            {
                "timestamp": log['recorded_at'].isoformat() if isinstance(log['recorded_at'], datetime) else str(log['recorded_at']),
                "transfer_rx": log['transfer_rx'],
                "transfer_tx": log['transfer_tx'],
                "transfer_total": log['transfer_total']
            }
            for log in logs
        ],
        "count": len(logs)
    }


@router.get("/user/{username}", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def get_user_analytics(
    username: str,
    request: Request,
    hours: int = Query(24, ge=1, le=168)
):
    """
    Get analytics untuk specific user (admin only)
    """
    verify_jwt_admin(request)
    
    # Get traffic summary untuk user
    summary = get_traffic_summary(ldap_uid=username, hours=hours)
    
    # Get traffic logs
    start_time = datetime.now() - timedelta(hours=hours)
    logs = get_traffic_logs(
        ldap_uid=username,
        start_time=start_time,
        limit=1000
    )
    
    return {
        "status": "ok",
        "username": username,
        "summary": summary,
        "logs": [
            {
                "timestamp": log['recorded_at'].isoformat() if isinstance(log['recorded_at'], datetime) else str(log['recorded_at']),
                "device_id": log['device_id'],
                "transfer_rx": log['transfer_rx'],
                "transfer_tx": log['transfer_tx'],
                "transfer_total": log['transfer_total']
            }
            for log in logs
        ],
        "count": len(logs)
    }


@router.post("/sync", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def manual_sync_traffic(request: Request):
    """
    Manual trigger traffic sync (admin only)
    """
    verify_jwt_admin(request)
    
    from app.core.background_jobs import job_manager
    
    try:
        stats = job_manager.run_manual_sync()
        return {
            "status": "ok",
            "message": "Traffic sync completed",
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error in manual sync: {e}")
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
