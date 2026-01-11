"""
Device Management Endpoints
CRUD operations untuk VPN devices
"""

from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt
from app.core.ldap_client import check_wireguard_enabled
from app.services.device_service import (
    create_user_device,
    revoke_user_device,
    get_device_info,
    validate_device_name,
    can_add_device,
    regenerate_qr_code
)
from app.database.queries import get_user_devices, get_qr_code, clear_qr_code
from app.core.cache import cached, clear_cache_prefix
from app.logger import logger

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.post("/add", dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def add_device(data: dict, request: Request):
    """
    Add new VPN device
    Requires: device_name
    """
    username = verify_jwt(request)
    
    device_name = data.get("device_name")
    if not device_name:
        raise HTTPException(status_code=400, detail="device_name is required")
    
    # Check wireguardEnabled
    if not check_wireguard_enabled(username):
        raise HTTPException(
            status_code=403,
            detail="WireGuard access is disabled. Please contact administrator."
        )
    
    try:
        # Get client IP and User-Agent untuk device fingerprinting
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", None)
        
        result = create_user_device(username, device_name, user_agent=user_agent, client_ip=client_ip)
        
        # QR code sudah di-generate di service dan disimpan di database
        logger.info(f"Device added: User={username}, Device={device_name}, ID={result['device_id']}, IP={client_ip}")
        
        return {
            "status": "ok",
            "message": "Device created successfully",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding device: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create device: {str(e)}")


@router.get("/", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def list_devices(request: Request, include_revoked: bool = False):
    """
    List all devices untuk logged-in user
    Note: Cache di-handle di service level untuk better control
    """
    username = verify_jwt(request)
    
    devices = get_user_devices(username, include_revoked=include_revoked)
    
    # Format response
    device_list = []
    for device in devices:
        device_list.append({
            "device_id": device['id'],
            "device_name": device['device_name'],
            "vpn_ip": device['vpn_ip'],
            "public_key": device['public_key'],
            "status": device['status'],
            "created_at": device['created_at'].isoformat() if isinstance(device['created_at'], datetime) else str(device['created_at']),
            "last_seen": device['last_seen'].isoformat() if device['last_seen'] and isinstance(device['last_seen'], datetime) else (str(device['last_seen']) if device['last_seen'] else None),
            "transfer_rx": device.get('transfer_rx', 0),
            "transfer_tx": device.get('transfer_tx', 0),
            "transfer_total": device.get('transfer_total', 0)
        })
    
    return {
        "status": "ok",
        "username": username,
        "devices": device_list,
        "count": len(device_list)
    }


@router.get("/{device_id}")
def get_device(device_id: int, request: Request):
    """
    Get device details
    """
    username = verify_jwt(request)
    
    try:
        device_info = get_device_info(device_id, username)
        return {
            "status": "ok",
            **device_info
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{device_id}")
def delete_device(device_id: int, request: Request):
    """
    Revoke/delete device
    """
    username = verify_jwt(request)
    
    revoke_reason = f"Revoked by user {username}"
    
    try:
        success = revoke_user_device(device_id, username, revoke_reason)
        
        if success:
            return {
                "status": "ok",
                "message": "Device revoked successfully",
                "device_id": device_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to revoke device")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error revoking device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{device_id}/config")
def get_device_config(device_id: int, request: Request):
    """
    Get device config untuk download
    Note: Private key tidak tersedia karena tidak disimpan
    User perlu regenerate device jika kehilangan private key
    """
    username = verify_jwt(request)
    
    device = get_device_info(device_id, username)
    
    if device['status'] != 'active':
        raise HTTPException(status_code=400, detail=f"Cannot get config for {device['status']} device")
    
    return {
        "status": "ok",
        "device_id": device_id,
        "device_name": device['device_name'],
        "vpn_ip": device['vpn_ip'],
        "public_key": device['public_key'],
        "note": "Private key tidak tersedia. Jika kehilangan private key, revoke device ini dan buat device baru."
    }


@router.get("/{device_id}/qr")
def get_device_qr(device_id: int, request: Request):
    """
    Get QR code untuk device
    Returns QR code jika masih valid (belum expired)
    Jika expired atau tidak ada, return error dengan option untuk regenerate
    """
    username = verify_jwt(request)
    
    device = get_device_info(device_id, username)
    
    if device['status'] != 'active':
        raise HTTPException(status_code=400, detail=f"Cannot get QR for {device['status']} device")
    
    # Get QR code dari database
    qr_data = get_qr_code(device_id)
    
    if qr_data:
        # QR code masih valid
        return {
            "status": "ok",
            "device_id": device_id,
            "qr_code": qr_data['qr_code_base64'],
            "expires_at": qr_data['expires_at'],
            "expired": False
        }
    else:
        # QR code expired atau tidak ada, bisa regenerate
        raise HTTPException(
            status_code=404,
            detail="QR code tidak tersedia atau sudah expired. Gunakan endpoint POST /devices/{device_id}/qr/regenerate untuk membuat QR code baru."
        )


@router.post("/{device_id}/qr/regenerate", dependencies=[Depends(RateLimiter(times=3, seconds=60))])
def regenerate_device_qr(device_id: int, request: Request):
    """
    Regenerate QR code untuk device
    QR code akan expire dalam 30 menit
    """
    username = verify_jwt(request)
    
    try:
        result = regenerate_qr_code(device_id, username)
        
        return {
            "status": "ok",
            "message": "QR code regenerated successfully",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error regenerating QR code for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate QR code: {str(e)}")


@router.get("/check/limit")
def check_device_limit(request: Request):
    """
    Check device limit dan current count
    """
    username = verify_jwt(request)
    
    can_add, reason = can_add_device(username)
    current_count = len(get_user_devices(username, include_revoked=False))
    
    from app.core.ldap_client import get_max_devices
    max_devices = get_max_devices(username)
    
    return {
        "status": "ok",
        "can_add": can_add,
        "reason": reason if not can_add else "OK",
        "current_count": current_count,
        "max_devices": max_devices,
        "wireguard_enabled": check_wireguard_enabled(username)
    }
