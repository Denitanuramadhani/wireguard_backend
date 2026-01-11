"""
Pytest configuration and fixtures
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "True"
os.environ["MYSQL_HOST"] = "localhost"
os.environ["MYSQL_DATABASE"] = "wireguard_vpn_test"
os.environ["JWT_SECRET"] = "test_secret_key_for_testing_only"
os.environ["LDAP_SERVER"] = "ldap://localhost:389"
os.environ["LDAP_BASE_DN"] = "dc=test,dc=com"

from app.main import app


@pytest.fixture
def client():
    """Test client untuk FastAPI"""
    return TestClient(app)


@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    with patch('app.database.connection.get_db_connection') as mock:
        yield mock


@pytest.fixture
def mock_ldap_connection():
    """Mock LDAP connection"""
    with patch('app.core.ldap_client.get_ldap_connection') as mock:
        yield mock


@pytest.fixture
def mock_wireguard_command():
    """Mock WireGuard commands"""
    with patch('subprocess.check_output') as mock:
        mock.return_value = b"test_public_key\t(none)\t(none)\t10.8.0.5/32\t0\t1024\t2048"
        yield mock


@pytest.fixture
def sample_device_data():
    """Sample device data untuk testing"""
    return {
        "id": 1,
        "ldap_uid": "testuser",
        "device_name": "test-device",
        "public_key": "test_public_key_1234567890",
        "vpn_ip": "10.8.0.5",
        "status": "active",
        "transfer_rx": 1024,
        "transfer_tx": 2048,
        "transfer_total": 3072,
        "created_at": "2024-01-01T00:00:00",
        "last_seen": None
    }


@pytest.fixture
def sample_user_data():
    """Sample user data untuk testing"""
    return {
        "username": "testuser",
        "wireguard_enabled": True,
        "max_devices": 3
    }


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token untuk testing"""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0dXNlciIsImV4cCI6OTk5OTk5OTk5OX0.test_signature"
