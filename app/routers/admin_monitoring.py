"""
Admin Monitoring & Alerts Endpoints
"""

from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt_admin
from app.core.audit_logger import get_audit_logs
from app.core.alert_system import get_recent_alerts, send_alert
from app.database.queries import get_all_devices
from app.logger import logger

router = APIRouter(prefix="/admin/monitoring", tags=["Admin - Monitoring"])


@router.get("/alerts")
def get_alerts(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    severity: str = Query(None, regex="^(low|medium|high|critical)$")
):
    """
    Get recent alerts
    Admin only
    """
    verify_jwt_admin(request)
    
    alerts = get_recent_alerts(limit=limit, severity=severity)
    
    return {
        "status": "ok",
        "alerts": alerts,
        "count": len(alerts)
    }


@router.get("/audit-logs")
def get_audit_logs_endpoint(
    request: Request,
    action: str = Query(None),
    ldap_uid: str = Query(None),
    performed_by: str = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """
    Get audit logs dengan filtering
    Admin only
    """
    verify_jwt_admin(request)
    
    logs = get_audit_logs(
        action=action,
        ldap_uid=ldap_uid,
        performed_by=performed_by,
        limit=limit,
        offset=offset
    )
    
    return {
        "status": "ok",
        "logs": logs,
        "count": len(logs),
        "limit": limit,
        "offset": offset
    }


@router.get("/stats")
def get_system_stats(request: Request):
    """
    Get system statistics
    Admin only
    """
    verify_jwt_admin(request)
    
    try:
        # Get device statistics
        all_devices = get_all_devices(status=None)
        active_devices = [d for d in all_devices if d['status'] == 'active']
        revoked_devices = [d for d in all_devices if d['status'] == 'revoked']
        
        # Get unique users
        unique_users = set(d['ldap_uid'] for d in all_devices)
        
        # Get recent alerts count
        recent_alerts = get_recent_alerts(limit=100)
        critical_alerts = [a for a in recent_alerts if a['severity'] == 'critical']
        high_alerts = [a for a in recent_alerts if a['severity'] == 'high']
        
        return {
            "status": "ok",
            "statistics": {
                "devices": {
                    "total": len(all_devices),
                    "active": len(active_devices),
                    "revoked": len(revoked_devices)
                },
                "users": {
                    "total_with_devices": len(unique_users)
                },
                "alerts": {
                    "total_recent": len(recent_alerts),
                    "critical": len(critical_alerts),
                    "high": len(high_alerts)
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
