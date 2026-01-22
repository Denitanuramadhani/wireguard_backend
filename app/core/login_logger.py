"""
Login Logger Module
Helper functions untuk logging login events ke file khusus login.log
"""

from datetime import datetime
from typing import Optional, Dict, Any
from app.logger import login_logger


def log_login_attempt(
    username: str,
    ip_address: str,
    user_agent: Optional[str] = None,
    success: bool = False,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    wireguard_enabled: Optional[bool] = None,
    max_devices: Optional[int] = None,
    **kwargs
):
    """
    Log login attempt dengan detail lengkap
    
    Args:
        username: Username yang mencoba login
        ip_address: IP address client
        user_agent: User agent string (optional)
        success: True jika login berhasil, False jika gagal
        error_type: Type error jika login gagal (optional)
        error_message: Error message jika login gagal (optional)
        wireguard_enabled: WireGuard enabled status (optional)
        max_devices: Max devices allowed (optional)
        **kwargs: Additional details untuk log
    """
    status = "SUCCESS" if success else "FAILED"
    
    # Build log message dengan format yang mudah di-parse
    log_parts = [
        f"LOGIN {status}",
        f"username={username}",
        f"ip={ip_address}"
    ]
    
    if user_agent:
        log_parts.append(f"user_agent={user_agent[:100]}")  # Limit panjang user agent
    
    if success:
        if wireguard_enabled is not None:
            log_parts.append(f"wireguard_enabled={wireguard_enabled}")
        if max_devices is not None:
            log_parts.append(f"max_devices={max_devices}")
    else:
        if error_type:
            log_parts.append(f"error_type={error_type}")
        if error_message:
            # Escape newlines dan limit panjang error message
            error_msg_clean = error_message.replace("\n", " ").replace("\r", "")[:200]
            log_parts.append(f"error={error_msg_clean}")
    
    # Add additional details jika ada
    if kwargs:
        for key, value in kwargs.items():
            if value is not None:
                log_parts.append(f"{key}={value}")
    
    log_message = " | ".join(log_parts)
    
    # Log dengan level sesuai status
    if success:
        login_logger.info(log_message)
    else:
        login_logger.warning(log_message)


def log_login_success(
    username: str,
    ip_address: str,
    user_agent: Optional[str] = None,
    wireguard_enabled: bool = False,
    max_devices: int = 3,
    **kwargs
):
    """
    Log successful login
    
    Args:
        username: Username yang berhasil login
        ip_address: IP address client
        user_agent: User agent string (optional)
        wireguard_enabled: WireGuard enabled status
        max_devices: Max devices allowed
        **kwargs: Additional details
    """
    log_login_attempt(
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=True,
        wireguard_enabled=wireguard_enabled,
        max_devices=max_devices,
        **kwargs
    )


def log_login_failed(
    username: str,
    ip_address: str,
    user_agent: Optional[str] = None,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    reason: Optional[str] = None,
    **kwargs
):
    """
    Log failed login attempt
    
    Args:
        username: Username yang gagal login
        ip_address: IP address client
        user_agent: User agent string (optional)
        error_type: Type error (optional)
        error_message: Error message (optional)
        reason: Reason for failure (e.g., "invalid_credentials", "ldap_error", etc.)
        **kwargs: Additional details
    """
    if reason:
        kwargs["reason"] = reason
    
    log_login_attempt(
        username=username,
        ip_address=ip_address,
        user_agent=user_agent,
        success=False,
        error_type=error_type,
        error_message=error_message,
        **kwargs
    )


def log_refresh_token(
    username: str,
    ip_address: str,
    success: bool = False,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    **kwargs
):
    """
    Log refresh token attempt
    
    Args:
        username: Username yang mencoba refresh token
        ip_address: IP address client
        success: True jika refresh berhasil
        error_type: Type error jika refresh gagal (optional)
        error_message: Error message jika refresh gagal (optional)
        **kwargs: Additional details
    """
    status = "SUCCESS" if success else "FAILED"
    
    log_parts = [
        f"REFRESH TOKEN {status}",
        f"username={username}",
        f"ip={ip_address}"
    ]
    
    if not success:
        if error_type:
            log_parts.append(f"error_type={error_type}")
        if error_message:
            error_msg_clean = error_message.replace("\n", " ").replace("\r", "")[:200]
            log_parts.append(f"error={error_msg_clean}")
    
    if kwargs:
        for key, value in kwargs.items():
            if value is not None:
                log_parts.append(f"{key}={value}")
    
    log_message = " | ".join(log_parts)
    
    if success:
        login_logger.info(log_message)
    else:
        login_logger.warning(log_message)
