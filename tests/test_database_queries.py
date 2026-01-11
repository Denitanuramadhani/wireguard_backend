"""
Unit tests untuk Database Queries
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.database.queries import (
    allocate_ip,
    create_device,
    get_user_devices,
    get_device_by_id,
    revoke_device,
    update_device_traffic,
    count_user_devices
)


class TestAllocateIP:
    """Test IP allocation"""
    
    @patch('app.database.queries.get_db_connection')
    def test_allocate_ip_success(self, mock_conn):
        # Mock database connection
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [None, None, None]  # First 3 IPs available
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        ip = allocate_ip("testuser")
        assert ip.startswith("10.8.0.")
        assert ip != "10.8.0.1"  # Should not be server IP
    
    @patch('app.database.queries.get_db_connection')
    def test_allocate_ip_no_available(self, mock_conn):
        # Mock: all IPs taken
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1}  # All IPs taken
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        with pytest.raises(Exception, match="No IP available"):
            allocate_ip("testuser")


class TestCreateDevice:
    """Test create_device function"""
    
    @patch('app.database.queries.get_db_connection')
    def test_create_device_success(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 1
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value.commit = MagicMock()
        
        device_id = create_device(
            ldap_uid="testuser",
            device_name="test-device",
            public_key="test_key",
            vpn_ip="10.8.0.5"
        )
        
        assert device_id == 1
        mock_cursor.execute.assert_called_once()


class TestGetUserDevices:
    """Test get_user_devices function"""
    
    @patch('app.database.queries.get_db_connection')
    def test_get_user_devices_success(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "id": 1,
                "ldap_uid": "testuser",
                "device_name": "device1",
                "status": "active"
            }
        ]
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        
        devices = get_user_devices("testuser")
        assert len(devices) == 1
        assert devices[0]["ldap_uid"] == "testuser"


class TestUpdateDeviceTraffic:
    """Test update_device_traffic function"""
    
    @patch('app.database.queries.get_db_connection')
    def test_update_traffic_success(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        mock_conn.return_value.__enter__.return_value.commit = MagicMock()
        
        result = update_device_traffic(
            public_key="test_key",
            transfer_rx=1024,
            transfer_tx=2048,
            last_seen=datetime.now()
        )
        
        assert result == True
        mock_cursor.execute.assert_called_once()
