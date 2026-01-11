"""
Alert System
Sends alerts untuk critical events
"""

from datetime import datetime
from typing import List, Dict, Any
from app.logger import logger
from app.core.audit_logger import log_audit_event


class AlertManager:
    """
    Manages alerts untuk critical events
    """
    
    def __init__(self):
        self.alert_history: List[Dict[str, Any]] = []
        self.max_history = 1000
    
    def send_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any] = None
    ):
        """
        Send alert untuk critical event
        alert_type: Type of alert (device_added, device_revoked, bandwidth_exceeded, etc.)
        severity: low, medium, high, critical
        message: Alert message
        details: Additional details
        """
        alert = {
            "alert_type": alert_type,
            "severity": severity,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Log alert
        logger.warning(f"ALERT [{severity.upper()}]: {alert_type} - {message}")
        
        # Add to history
        self.alert_history.append(alert)
        if len(self.alert_history) > self.max_history:
            self.alert_history.pop(0)
        
        # Log to audit log
        log_audit_event(
            action=f"alert_{alert_type}",
            performed_by="system",
            details={
                "severity": severity,
                "message": message,
                **details or {}
            }
        )
        
        # TODO: Send to external alerting system (email, Slack, etc.)
        # For now, just log to file and database
    
    def get_recent_alerts(self, limit: int = 50, severity: str = None) -> List[Dict[str, Any]]:
        """
        Get recent alerts
        """
        alerts = self.alert_history[-limit:] if limit else self.alert_history
        
        if severity:
            alerts = [a for a in alerts if a['severity'] == severity]
        
        return list(reversed(alerts))  # Most recent first


# Global alert manager instance
alert_manager = AlertManager()


def send_alert(alert_type: str, severity: str, message: str, details: Dict[str, Any] = None):
    """Convenience function untuk send alert"""
    alert_manager.send_alert(alert_type, severity, message, details)


def get_recent_alerts(limit: int = 50, severity: str = None) -> List[Dict[str, Any]]:
    """Convenience function untuk get recent alerts"""
    return alert_manager.get_recent_alerts(limit, severity)
