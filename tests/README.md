# Testing Guide

## Setup Testing Environment

```bash
# Install test dependencies
pip install -r requirements.txt

# Setup test database (optional, untuk integration tests)
# Create test database di MySQL
mysql -u root -p
CREATE DATABASE wireguard_vpn_test;
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test File
```bash
pytest tests/test_device_service.py
```

### Run Specific Test
```bash
pytest tests/test_device_service.py::TestValidateDeviceName::test_valid_device_name
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Run Only Unit Tests
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Run Tests with Verbose Output
```bash
pytest -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Pytest fixtures
├── test_device_service.py
├── test_database_queries.py
├── test_ldap_client.py
├── test_integration.py
├── test_utils.py
└── README.md
```

## Test Categories

### Unit Tests
- Test individual functions/modules
- Mock external dependencies
- Fast execution
- Marked with `@pytest.mark.unit`

### Integration Tests
- Test full flow
- May require real services (database, LDAP)
- Slower execution
- Marked with `@pytest.mark.integration`

## Writing New Tests

### Example Unit Test
```python
import pytest
from app.services.device_service import validate_device_name

def test_validate_device_name_valid():
    assert validate_device_name("my-device") == True

def test_validate_device_name_invalid():
    assert validate_device_name("") == False
```

### Example Integration Test
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_flow():
    response = client.post("/auth/login", json={
        "username": "test",
        "password": "test"
    })
    assert response.status_code == 200
```

## Test Fixtures

Available fixtures (defined in `conftest.py`):
- `client` - FastAPI test client
- `mock_db_connection` - Mock database connection
- `mock_ldap_connection` - Mock LDAP connection
- `mock_wireguard_command` - Mock WireGuard commands
- `sample_device_data` - Sample device data
- `sample_user_data` - Sample user data
- `mock_jwt_token` - Mock JWT token

## Continuous Integration

Tests should be run:
- Before every commit
- In CI/CD pipeline
- Before deployment

## Coverage Goals

- Unit tests: > 80% coverage
- Critical paths: 100% coverage
- Integration tests: Cover main user flows

---

*Testing framework untuk WireGuard VPN Portal Backend*
