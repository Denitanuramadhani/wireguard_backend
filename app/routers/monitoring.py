"""
User Monitoring Endpoints
User bisa lihat monitoring untuk device mereka sendiri
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt
from app.core.audit_logger import get_audit_logs
from app.database.queries import get_user_devices
from app.logger import logger

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/audit-logs", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def get_user_audit_logs(
    request: Request,
    action: str = Query(None, description="Filter by action type"),
    limit: int = Query(50, ge=1, le=500, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get audit logs untuk user sendiri
    User hanya bisa lihat audit logs yang terkait dengan mereka (ldap_uid atau performed_by)
    """
    username = verify_jwt(request)
    
    # User hanya bisa lihat logs yang terkait dengan mereka
    # Get logs where user is the subject (ldap_uid)
    logs_subject = get_audit_logs(
        action=action,
        ldap_uid=username,
        performed_by=None,
        limit=1000,  # Get more to combine
        offset=0
    )
    
    # Get logs where user performed the action
    logs_performed = get_audit_logs(
        action=action,
        ldap_uid=None,
        performed_by=username,
        limit=1000,  # Get more to combine
        offset=0
    )
    
    # Combine and deduplicate by id
    all_logs = {}
    for log in logs_subject + logs_performed:
        log_id = log.get('id')
        if log_id and log_id not in all_logs:
            all_logs[log_id] = log
    
    # Sort by created_at descending
    result_logs = list(all_logs.values())
    result_logs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    # Apply pagination
    total = len(result_logs)
    paginated_logs = result_logs[offset:offset+limit]
    
    return {
        "status": "ok",
        "logs": paginated_logs,
        "count": len(paginated_logs),
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/devices", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def get_user_devices_monitoring(
    request: Request,
    status: str = Query(None, description="Filter by device status: active, revoked, expired"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get user's devices dengan monitoring info
    User hanya bisa lihat device mereka sendiri
    """
    username = verify_jwt(request)
    
    devices = get_user_devices(username, include_revoked=True)
    
    # Filter by status if provided
    if status:
        devices = [d for d in devices if d.get('status') == status]
    
    # Pagination
    total = len(devices)
    devices = devices[offset:offset+limit]
    
    # Format devices
    device_list = []
    for device in devices:
        device_list.append({
            "device_id": device['id'],
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip'],
            "status": device['status'],
            "created_at": device['created_at'].isoformat() if hasattr(device['created_at'], 'isoformat') else str(device['created_at']),
            "last_seen": device['last_seen'].isoformat() if device.get('last_seen') and hasattr(device['last_seen'], 'isoformat') else (str(device['last_seen']) if device.get('last_seen') else None),
            "transfer_rx": device.get('transfer_rx', 0),
            "transfer_tx": device.get('transfer_tx', 0),
            "transfer_total": device.get('transfer_total', 0)
        })
    
    return {
        "status": "ok",
        "devices": device_list,
        "count": len(device_list),
        "total": total,
        "limit": limit,
        "offset": offset
    }

