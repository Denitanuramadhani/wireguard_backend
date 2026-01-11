"""
Unit tests untuk Device Service
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.device_service import (
    validate_device_name,
    can_add_device,
    create_user_device,
    revoke_user_device,
    get_device_info
)
from app.core.ldap_client import check_wireguard_enabled, get_max_devices
from app.database.queries import count_user_devices


class TestValidateDeviceName:
    """Test device name validation"""
    
    def test_valid_device_name(self):
        assert validate_device_name("my-laptop") == True
        assert validate_device_name("my_laptop") == True
        assert validate_device_name("device123") == True
        assert validate_device_name("a" * 50) == True  # Max length
    
    def test_invalid_device_name(self):
        assert validate_device_name("") == False
        assert validate_device_name("a" * 51) == False  # Too long
        assert validate_device_name("device name") == False  # Space
        assert validate_device_name("device@name") == False  # Special char
        assert validate_device_name("device.name") == False  # Dot


class TestCanAddDevice:
    """Test can_add_device function"""
    
    @patch('app.services.device_service.check_wireguard_enabled')
    @patch('app.services.device_service.count_user_devices')
    @patch('app.services.device_service.get_max_devices')
    def test_can_add_device_success(self, mock_max, mock_count, mock_enabled):
        mock_enabled.return_value = True
        mock_count.return_value = 1
        mock_max.return_value = 3
        
        can_add, reason = can_add_device("testuser")
        assert can_add == True
        assert reason == "OK"
    
    @patch('app.services.device_service.check_wireguard_enabled')
    def test_cannot_add_device_disabled(self, mock_enabled):
        mock_enabled.return_value = False
        
        can_add, reason = can_add_device("testuser")
        assert can_add == False
        assert "disabled" in reason.lower()
    
    @patch('app.services.device_service.check_wireguard_enabled')
    @patch('app.services.device_service.count_user_devices')
    @patch('app.services.device_service.get_max_devices')
    def test_cannot_add_device_limit_reached(self, mock_max, mock_count, mock_enabled):
        mock_enabled.return_value = True
        mock_count.return_value = 3
        mock_max.return_value = 3
        
        can_add, reason = can_add_device("testuser")
        assert can_add == False
        assert "limit" in reason.lower()


class TestCreateUserDevice:
    """Test create_user_device function"""
    
    @patch('app.services.device_service.can_add_device')
    @patch('app.services.device_service.get_user_devices')
    @patch('app.services.device_service.generate_keypair')
    @patch('app.services.device_service.allocate_ip')
    @patch('app.services.device_service.create_device')
    @patch('app.services.device_service.add_peer_to_wg')
    @patch('app.services.device_service.generate_client_config_text')
    def test_create_device_success(
        self, mock_config, mock_add_peer, mock_create, 
        mock_allocate, mock_keypair, mock_get_devices, mock_can_add
    ):
        # Setup mocks
        mock_can_add.return_value = (True, "OK")
        mock_get_devices.return_value = []
        mock_keypair.return_value = ("private_key", "public_key")
        mock_allocate.return_value = "10.8.0.5"
        mock_create.return_value = 1
        mock_config.return_value = "[Interface]\nPrivateKey=..."
        
        result = create_user_device("testuser", "my-device")
        
        assert result["device_id"] == 1
        assert result["device_name"] == "my-device"
        assert result["vpn_ip"] == "10.8.0.5"
        assert "config" in result
        mock_add_peer.assert_called_once()
    
    def test_create_device_invalid_name(self):
        with pytest.raises(ValueError):
            create_user_device("testuser", "")
    
    @patch('app.services.device_service.can_add_device')
    def test_create_device_permission_denied(self, mock_can_add):
        mock_can_add.return_value = (False, "Access denied")
        
        with pytest.raises(PermissionError):
            create_user_device("testuser", "my-device")
    
    @patch('app.services.device_service.can_add_device')
    @patch('app.services.device_service.get_user_devices')
    def test_create_device_duplicate_name(self, mock_get_devices, mock_can_add):
        mock_can_add.return_value = (True, "OK")
        mock_get_devices.return_value = [{"device_name": "my-device"}]
        
        with pytest.raises(ValueError, match="already exists"):
            create_user_device("testuser", "my-device")


class TestRevokeUserDevice:
    """Test revoke_user_device function"""
    
    @patch('app.services.device_service.get_device_by_id')
    @patch('app.services.device_service.remove_peer_from_wg')
    @patch('app.services.device_service.revoke_device')
    def test_revoke_device_success(self, mock_revoke, mock_remove, mock_get):
        mock_get.return_value = {
            "id": 1,
            "ldap_uid": "testuser",
            "public_key": "test_key",
            "status": "active"
        }
        mock_revoke.return_value = True
        
        result = revoke_user_device(1, "testuser")
        assert result == True
        mock_remove.assert_called_once()
        mock_revoke.assert_called_once()
    
    @patch('app.services.device_service.get_device_by_id')
    def test_revoke_device_not_found(self, mock_get):
        mock_get.return_value = None
        
        with pytest.raises(ValueError, match="not found"):
            revoke_user_device(1, "testuser")
    
    @patch('app.services.device_service.get_device_by_id')
    def test_revoke_device_already_revoked(self, mock_get):
        mock_get.return_value = {
            "id": 1,
            "ldap_uid": "testuser",
            "status": "revoked"
        }
        
        with pytest.raises(ValueError, match="already"):
            revoke_user_device(1, "testuser")
