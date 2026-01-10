"""
Traffic Monitor Service
Sync traffic data dari WireGuard ke MySQL
"""

from datetime import datetime, timedelta
import subprocess
from app.database.queries import (
    get_device_by_public_key,
    update_device_traffic,
    insert_traffic_log,
    get_all_devices
)
from app.logger import logger


def parse_wireguard_dump() -> list:
    """
    Parse output dari 'wg show wg0 dump'
    Returns list of peer info dictionaries
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
            latest_handshake_str = cols[4] if len(cols) > 4 and cols[4] != "0" else None
            transfer_rx = int(cols[5]) if len(cols) > 5 else 0
            transfer_tx = int(cols[6]) if len(cols) > 6 else 0
            
            # Parse latest handshake
            last_seen = None
            if latest_handshake_str and latest_handshake_str != "0":
                try:
                    seconds_ago = int(latest_handshake_str)
                    last_seen = datetime.now() - timedelta(seconds=seconds_ago)
                except:
                    pass
            
            peers.append({
                "public_key": public_key,
                "transfer_rx": transfer_rx,
                "transfer_tx": transfer_tx,
                "last_seen": last_seen,
                "endpoint": endpoint,
                "allowed_ips": allowed_ips
            })
        
        return peers
    except Exception as e:
        logger.error(f"Error parsing WireGuard dump: {e}")
        return []


def sync_traffic_data() -> dict:
    """
    Sync traffic data dari WireGuard ke MySQL
    Returns dict dengan sync statistics
    """
    stats = {
        "peers_found": 0,
        "devices_updated": 0,
        "logs_inserted": 0,
        "errors": 0,
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        # Get peers dari WireGuard
        wg_peers = parse_wireguard_dump()
        stats["peers_found"] = len(wg_peers)
        
        for peer in wg_peers:
            public_key = peer["public_key"]
            transfer_rx = peer["transfer_rx"]
            transfer_tx = peer["transfer_tx"]
            last_seen = peer["last_seen"]
            
            # Get device dari MySQL
            device = get_device_by_public_key(public_key)
            
            if device:
                # Update device traffic
                success = update_device_traffic(
                    public_key=public_key,
                    transfer_rx=transfer_rx,
                    transfer_tx=transfer_tx,
                    last_seen=last_seen
                )
                
                if success:
                    stats["devices_updated"] += 1
                    
                    # Insert traffic log untuk analytics
                    log_success = insert_traffic_log(
                        device_id=device['id'],
                        ldap_uid=device['ldap_uid'],
                        public_key=public_key,
                        transfer_rx=transfer_rx,
                        transfer_tx=transfer_tx
                    )
                    
                    if log_success:
                        stats["logs_inserted"] += 1
                else:
                    stats["errors"] += 1
                    logger.warning(f"Failed to update traffic for device {device['id']}")
            else:
                # Peer ada di WireGuard tapi tidak di MySQL
                logger.warning(f"Peer {public_key[:20]}... found in WireGuard but not in MySQL")
        
        logger.info(f"Traffic sync completed: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Error syncing traffic data: {e}")
        stats["errors"] += 1
        return stats


def get_traffic_summary(device_id: int = None, ldap_uid: str = None, hours: int = 24) -> dict:
    """
    Get traffic summary untuk device atau user
    Returns summary statistics
    """
    from app.database.connection import get_db_connection
    
    since = datetime.now() - timedelta(hours=hours)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT 
                SUM(transfer_rx) as total_rx,
                SUM(transfer_tx) as total_tx,
                SUM(transfer_total) as total,
                COUNT(*) as log_count
            FROM vpn_traffic_logs
            WHERE recorded_at >= %s
        """
        params = [since]
        
        if device_id:
            query += " AND device_id = %s"
            params.append(device_id)
        elif ldap_uid:
            query += " AND ldap_uid = %s"
            params.append(ldap_uid)
        
        cursor.execute(query, params)
        result = cursor.fetchone()
        
        return {
            "total_rx": result['total_rx'] or 0,
            "total_tx": result['total_tx'] or 0,
            "total": result['total'] or 0,
            "log_count": result['log_count'] or 0,
            "hours": hours,
            "since": since.isoformat()
        }
