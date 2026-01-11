"""
Integration tests untuk full flow
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestAuthFlow:
    """Test authentication flow"""
    
    @patch('app.services.ldap_auth.ldap_authenticate')
    def test_login_success(self, mock_auth):
        mock_auth.return_value = True
        
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "password"}
        )
        
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert "refresh_token" in response.json()
    
    @patch('app.services.ldap_auth.ldap_authenticate')
    def test_login_failed(self, mock_auth):
        mock_auth.return_value = False
        
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "wrong"}
        )
        
        assert response.status_code == 401


class TestDeviceFlow:
    """Test device creation flow"""
    
    @patch('app.middleware.auth_middleware.verify_jwt')
    @patch('app.core.ldap_client.check_wireguard_enabled')
    @patch('app.services.device_service.create_user_device')
    def test_add_device_success(self, mock_create, mock_enabled, mock_verify):
        mock_verify.return_value = "testuser"
        mock_enabled.return_value = True
        mock_create.return_value = {
            "device_id": 1,
            "device_name": "my-device",
            "vpn_ip": "10.8.0.5",
            "config": "[Interface]...",
            "qr_code": {"qr_base64": "test"}
        }
        
        response = client.post(
            "/devices/add",
            headers={"Authorization": "Bearer test_token"},
            json={"device_name": "my-device"}
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert "device_id" in response.json()
    
    @patch('app.middleware.auth_middleware.verify_jwt')
    @patch('app.core.ldap_client.check_wireguard_enabled')
    def test_add_device_disabled(self, mock_enabled, mock_verify):
        mock_verify.return_value = "testuser"
        mock_enabled.return_value = False
        
        response = client.post(
            "/devices/add",
            headers={"Authorization": "Bearer test_token"},
            json={"device_name": "my-device"}
        )
        
        assert response.status_code == 403


class TestAdminFlow:
    """Test admin operations flow"""
    
    @patch('app.middleware.auth_middleware.verify_jwt_admin')
    @patch('app.database.queries.get_all_devices')
    def test_admin_list_devices(self, mock_get_devices, mock_verify):
        mock_verify.return_value = "admin"
        mock_get_devices.return_value = []
        
        response = client.get(
            "/admin/devices",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        assert response.status_code == 200
        assert "devices" in response.json()
    
    @patch('app.middleware.auth_middleware.verify_jwt_admin')
    @patch('app.core.ldap_client.enable_wireguard_user')
    def test_admin_enable_user(self, mock_enable, mock_verify):
        mock_verify.return_value = "admin"
        mock_enable.return_value = True
        
        response = client.post(
            "/admin/users/testuser/enable",
            headers={"Authorization": "Bearer admin_token"}
        )
        
        assert response.status_code == 200
        assert response.json()["wireguard_enabled"] == True
