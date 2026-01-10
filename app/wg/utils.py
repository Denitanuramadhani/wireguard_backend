"""
WireGuard Utility Functions
Helper functions untuk WireGuard operations
"""

import subprocess
from app.config import WG_INTERFACE
from app.logger import logger


def add_peer_to_wg(public_key: str, allowed_ip: str) -> bool:
    """
    Add peer ke WireGuard server
    Returns True jika berhasil
    """
    try:
        result = subprocess.run(
            ["sudo", "wg", "set", WG_INTERFACE, "peer", public_key, "allowed-ips", allowed_ip],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Peer added: {public_key[:20]}... IP: {allowed_ip}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error adding peer to WireGuard: {e.stderr}")
        raise Exception(f"Failed to add peer to WireGuard: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error adding peer: {e}")
        raise


def remove_peer_from_wg(public_key: str) -> bool:
    """
    Remove peer dari WireGuard server
    Returns True jika berhasil
    """
    try:
        result = subprocess.run(
            ["sudo", "wg", "set", WG_INTERFACE, "peer", public_key, "remove"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Peer removed: {public_key[:20]}...")
        return True
    except subprocess.CalledProcessError as e:
        # Peer mungkin sudah tidak ada, tidak error
        logger.warning(f"Peer removal warning: {e.stderr}")
        return True  # Return True karena tujuan sudah tercapai
    except Exception as e:
        logger.error(f"Unexpected error removing peer: {e}")
        raise
