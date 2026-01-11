"""
Background Jobs
Periodic tasks untuk sync traffic, cleanup, dll
"""

import asyncio
import threading
from datetime import datetime
from app.services.traffic_monitor import sync_traffic_data
from app.services.device_expiration import check_and_revoke_expired_devices
from app.logger import logger
from app.config import ENVIRONMENT


class BackgroundJobManager:
    """
    Manager untuk background jobs
    """
    def __init__(self):
        self.running = False
        self.traffic_sync_task = None
        self.device_expiration_task = None
    
    def start_traffic_sync(self, interval_seconds: int = 300):
        """
        Start periodic traffic sync job
        interval_seconds: Sync setiap N detik (default: 5 menit)
        """
        if self.running:
            logger.warning("Traffic sync job already running")
            return
        
        self.running = True
        
        def sync_loop():
            logger.info(f"Starting traffic sync job (interval: {interval_seconds}s)")
            while self.running:
                try:
                    stats = sync_traffic_data()
                    logger.debug(f"Traffic sync stats: {stats}")
                except Exception as e:
                    logger.error(f"Error in traffic sync job: {e}")
                
                # Sleep untuk interval
                for _ in range(interval_seconds):
                    if not self.running:
                        break
                    threading.Event().wait(1)
        
        self.traffic_sync_task = threading.Thread(target=sync_loop, daemon=True)
        self.traffic_sync_task.start()
        logger.info("Traffic sync job started")
    
    def start_device_expiration_check(self, interval_hours: int = 24):
        """
        Start periodic device expiration check job
        interval_hours: Check setiap N jam (default: 24 jam / 1 hari)
        """
        if self.device_expiration_task and self.device_expiration_task.is_alive():
            logger.warning("Device expiration check job already running")
            return
        
        def expiration_loop():
            logger.info(f"Starting device expiration check job (interval: {interval_hours}h)")
            while self.running:
                try:
                    stats = check_and_revoke_expired_devices()
                    logger.debug(f"Device expiration check stats: {stats}")
                except Exception as e:
                    logger.error(f"Error in device expiration check job: {e}")
                
                # Sleep untuk interval (dalam detik)
                interval_seconds = interval_hours * 3600
                for _ in range(interval_seconds):
                    if not self.running:
                        break
                    threading.Event().wait(1)
        
        self.device_expiration_task = threading.Thread(target=expiration_loop, daemon=True)
        self.device_expiration_task.start()
        logger.info("Device expiration check job started")
    
    def stop(self):
        """
        Stop all background jobs
        """
        self.running = False
        logger.info("Background jobs stopped")
    
    def run_manual_sync(self):
        """
        Run traffic sync manually (for testing or on-demand)
        """
        logger.info("Running manual traffic sync")
        return sync_traffic_data()


# Global instance
job_manager = BackgroundJobManager()


def start_background_jobs():
    """
    Start all background jobs
    """
    if ENVIRONMENT == "production":
        # Start traffic sync setiap 5 menit
        job_manager.start_traffic_sync(interval_seconds=300)
        # Start device expiration check setiap 24 jam
        job_manager.start_device_expiration_check(interval_hours=24)
    else:
        # Development: sync setiap 1 menit untuk testing
        job_manager.start_traffic_sync(interval_seconds=60)
        # Development: check expiration setiap 1 jam untuk testing
        job_manager.start_device_expiration_check(interval_hours=1)
    
    logger.info("All background jobs started")


def stop_background_jobs():
    """
    Stop all background jobs
    """
    job_manager.stop()
