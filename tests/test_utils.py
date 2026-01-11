"""
Test utilities dan helper functions
"""

import pytest
from app.wg.generator import generate_keypair, generate_client_config_text
from app.wg.utils import add_peer_to_wg, remove_peer_from_wg


class TestWireGuardGenerator:
    """Test WireGuard key generation"""
    
    @pytest.mark.unit
    def test_generate_keypair_format(self):
        """Test bahwa keypair yang di-generate memiliki format yang benar"""
        private_key, public_key = generate_keypair()
        
        assert len(private_key) > 0
        assert len(public_key) > 0
        # WireGuard keys biasanya base64 encoded, panjang sekitar 44 chars
        assert len(private_key) >= 40
        assert len(public_key) >= 40
    
    @pytest.mark.unit
    def test_generate_config_text(self):
        """Test config text generation"""
        private_key = "test_private_key_123456789012345678901234567890"
        public_key = "test_public_key_123456789012345678901234567890"
        client_ip = "10.8.0.5"
        
        config = generate_client_config_text(private_key, public_key, client_ip)
        
        assert "[Interface]" in config
        assert "[Peer]" in config
        assert private_key in config
        assert public_key in config
        assert client_ip in config


class TestInputValidation:
    """Test input validation"""
    
    @pytest.mark.unit
    def test_username_validation(self):
        """Test username validation"""
        from app.services.device_service import validate_device_name
        
        # Valid
        assert validate_device_name("user123") == True
        assert validate_device_name("user-name") == True
        assert validate_device_name("user_name") == True
        
        # Invalid
        assert validate_device_name("") == False
        assert validate_device_name("user name") == False  # Space
        assert validate_device_name("user@name") == False  # Special char
        assert validate_device_name("a" * 51) == False  # Too long
