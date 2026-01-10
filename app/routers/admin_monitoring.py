"""
Admin Monitoring Endpoints
Monitor peers, traffic, consistency
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi_limiter.depends import RateLimiter
from app.middleware.auth_middleware import verify_jwt_admin
from app.database.queries import get_all_devices, get_device_by_public_key
from app.logger import logger
import subprocess
import re

router = APIRouter(prefix="/admin", tags=["Admin"])


def get_wireguard_peers():
    """
    Get active peers dari WireGuard
    Returns list of peers dengan info lengkap
    """
    try:
        result = subprocess.check_output(
            ["sudo", "wg", "show", "wg0", "dump"],
            stderr=subprocess.STDOUT
        )
        lines = result.decode().strip().split("\n")
        
        peers = []
        for line in lines:
            if not line.strip():
                continue
            
            cols = line.split("\t")
            if len(cols) < 4:
                continue
            
            public_key = cols[0]
            preshared_key = cols[1] if cols[1] != "(none)" else None
            endpoint = cols[2] if cols[2] != "(none)" else None
            allowed_ips = cols[3]
            latest_handshake = cols[4] if len(cols) > 4 and cols[4] != "0" else None
            transfer_rx = int(cols[5]) if len(cols) > 5 else 0
            transfer_tx = int(cols[6]) if len(cols) > 6 else 0
            
            # Parse latest handshake
            handshake_time = None
            if latest_handshake and latest_handshake != "0":
                try:
                    seconds_ago = int(latest_handshake)
                    handshake_time = datetime.now() - timedelta(seconds=seconds_ago)
                except:
                    pass
            
            peers.append({
                "public_key": public_key,
                "preshared_key": preshared_key,
                "endpoint": endpoint,
                "allowed_ips": allowed_ips,
                "latest_handshake": handshake_time.isoformat() if handshake_time else None,
                "transfer_rx": transfer_rx,
                "transfer_tx": transfer_tx,
                "transfer_total": transfer_rx + transfer_tx
            })
        
        return peers
    except Exception as e:
        logger.error(f"Error getting WireGuard peers: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get WireGuard peers: {str(e)}")


@router.get("/monitoring/peers", dependencies=[Depends(RateLimiter(times=30, seconds=60))])
def get_active_peers(request: Request):
    """
    Get active WireGuard peers dengan info dari MySQL
    """
    verify_jwt_admin(request)
    
    # Get peers dari WireGuard
    wg_peers = get_wireguard_peers()
    
    # Enrich dengan info dari MySQL
    enriched_peers = []
    for peer in wg_peers:
        device = get_device_by_public_key(peer['public_key'])
        
        peer_info = {
            **peer,
            "device_id": device['id'] if device else None,
            "ldap_uid": device['ldap_uid'] if device else None,
            "device_name": device['device_name'] if device else None,
            "vpn_ip": device['vpn_ip'] if device else None,
            "status": device['status'] if device else "unknown",
            "in_database": device is not None
        }
        
        enriched_peers.append(peer_info)
    
    return {
        "status": "ok",
        "peers": enriched_peers,
        "count": len(enriched_peers),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/monitoring/consistency", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def check_consistency(request: Request):
    """
    Check consistency antara WireGuard peers dan MySQL database
    """
    verify_jwt_admin(request)
    
    # Get peers dari WireGuard
    wg_peers = get_wireguard_peers()
    wg_public_keys = {peer['public_key'] for peer in wg_peers}
    
    # Get active devices dari MySQL
    mysql_devices = get_all_devices(status='active')
    mysql_public_keys = {device['public_key'] for device in mysql_devices}
    
    # Find inconsistencies
    in_wg_not_mysql = wg_public_keys - mysql_public_keys
    in_mysql_not_wg = mysql_public_keys - wg_public_keys
    
    inconsistencies = []
    
    # Peers di WireGuard tapi tidak di MySQL
    for public_key in in_wg_not_mysql:
        peer = next((p for p in wg_peers if p['public_key'] == public_key), None)
        inconsistencies.append({
            "type": "in_wg_not_mysql",
            "public_key": public_key[:20] + "...",
            "allowed_ips": peer['allowed_ips'] if peer else None,
            "issue": "Peer exists in WireGuard but not in MySQL"
        })
    
    # Devices di MySQL tapi tidak di WireGuard
    for public_key in in_mysql_not_wg:
        device = next((d for d in mysql_devices if d['public_key'] == public_key), None)
        inconsistencies.append({
            "type": "in_mysql_not_wg",
            "public_key": public_key[:20] + "...",
            "device_id": device['id'] if device else None,
            "ldap_uid": device['ldap_uid'] if device else None,
            "device_name": device['device_name'] if device else None,
            "issue": "Device exists in MySQL but peer not in WireGuard"
        })
    
    return {
        "status": "ok",
        "consistent": len(inconsistencies) == 0,
        "wireguard_peers": len(wg_peers),
        "mysql_devices": len(mysql_devices),
        "inconsistencies": inconsistencies,
        "inconsistency_count": len(inconsistencies),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/monitoring/stats", dependencies=[Depends(RateLimiter(times=20, seconds=60))])
def get_monitoring_stats(request: Request):
    """
    Get overall monitoring statistics
    """
    verify_jwt_admin(request)
    
    # Get stats dari MySQL
    all_devices = get_all_devices(status=None, limit=10000)
    active_devices = [d for d in all_devices if d['status'] == 'active']
    revoked_devices = [d for d in all_devices if d['status'] == 'revoked']
    
    # Get WireGuard peers
    wg_peers = get_wireguard_peers()
    
    # Calculate totals
    total_transfer_rx = sum(d.get('transfer_rx', 0) for d in active_devices)
    total_transfer_tx = sum(d.get('transfer_tx', 0) for d in active_devices)
    total_transfer = total_transfer_rx + total_transfer_tx
    
    # Get unique users
    unique_users = len(set(d['ldap_uid'] for d in all_devices))
    
    return {
        "status": "ok",
        "devices": {
            "total": len(all_devices),
            "active": len(active_devices),
            "revoked": len(revoked_devices)
        },
        "wireguard_peers": len(wg_peers),
        "users": {
            "total": unique_users,
            "with_devices": unique_users
        },
        "traffic": {
            "total_rx": total_transfer_rx,
            "total_tx": total_transfer_tx,
            "total": total_transfer
        },
        "timestamp": datetime.now().isoformat()
    }
