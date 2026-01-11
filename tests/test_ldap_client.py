"""
Unit tests untuk LDAP Client
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.core.ldap_client import (
    check_wireguard_enabled,
    get_max_devices,
    enable_wireguard_user,
    disable_wireguard_user,
    is_admin
)


class TestCheckWireguardEnabled:
    """Test check_wireguard_enabled function"""
    
    @patch('app.core.ldap_client.get_user_attributes')
    def test_wireguard_enabled_true(self, mock_get_attrs):
        mock_get_attrs.return_value = {
            "objectClass": ["wireguardUser", "inetOrgPerson"],
            "wireguardEnabled": "TRUE"
        }
        
        result = check_wireguard_enabled("testuser")
        assert result == True
    
    @patch('app.core.ldap_client.get_user_attributes')
    def test_wireguard_enabled_false(self, mock_get_attrs):
        mock_get_attrs.return_value = {
            "objectClass": ["wireguardUser"],
            "wireguardEnabled": "FALSE"
        }
        
        result = check_wireguard_enabled("testuser")
        assert result == False
    
    @patch('app.core.ldap_client.get_user_attributes')
    def test_wireguard_enabled_no_objectclass(self, mock_get_attrs):
        mock_get_attrs.return_value = {
            "objectClass": ["inetOrgPerson"],
            "wireguardEnabled": "TRUE"
        }
        
        result = check_wireguard_enabled("testuser")
        assert result == False  # No wireguardUser objectClass


class TestGetMaxDevices:
    """Test get_max_devices function"""
    
    @patch('app.core.ldap_client.get_user_attributes')
    def test_get_max_devices_from_ldap(self, mock_get_attrs):
        mock_get_attrs.return_value = {
            "maxWireguardDevices": "5"
        }
        
        result = get_max_devices("testuser")
        assert result == 5
    
    @patch('app.core.ldap_client.get_user_attributes')
    def test_get_max_devices_default(self, mock_get_attrs):
        mock_get_attrs.return_value = {}
        
        result = get_max_devices("testuser")
        assert result == 3  # Default


class TestEnableWireguardUser:
    """Test enable_wireguard_user function"""
    
    @patch('app.core.ldap_client.get_ldap_connection')
    def test_enable_wireguard_success(self, mock_conn):
        mock_connection = MagicMock()
        mock_entry = MagicMock()
        mock_entry.objectClass.values = ["inetOrgPerson"]
        mock_connection.search.return_value = True
        mock_connection.entries = [mock_entry]
        mock_connection.result = {"description": "success"}
        mock_conn.return_value = mock_connection
        
        result = enable_wireguard_user("testuser")
        assert result == True
        mock_connection.modify.assert_called_once()


class TestIsAdmin:
    """Test is_admin function"""
    
    @patch('app.core.ldap_client.check_user_in_group')
    def test_is_admin_true(self, mock_check):
        mock_check.return_value = True
        
        result = is_admin("testuser")
        assert result == True
    
    @patch('app.core.ldap_client.check_user_in_group')
    def test_is_admin_false(self, mock_check):
        mock_check.return_value = False
        
        result = is_admin("testuser")
        assert result == False
