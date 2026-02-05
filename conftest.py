"""
Pytest configuration and fixtures for backend testing.

This module provides:
- Mock authentication for all tests
- Database fixtures (if needed)
- Reusable test clients with different user roles
- Utility fixtures for common test scenarios
"""

import pytest
import time
from fastapi.testclient import TestClient
from typing import Generator

import os
import sys

backend_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../dataforge/backend")
)
sys.path.insert(0, backend_path)
os.chdir(backend_path)

# Imports
from main import app
from app.libs.tenant_database import _tenant_cache
from app.libs.tenant_models import UserRole, UserTenantInfo
from databutton_app.mw.auth_mw import AuthorizedUser, get_authorized_user
from app.libs.auth import get_current_user

# Test User Configurations

# Standard test tenant
TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_TENANT_NAME = "Innoveria AS"
TEST_TENANT_SLUG = "innoveria"

# Different user roles for testing
TEST_USERS = {
    "admin": {
        "user_id": "test-admin-001",
        "role": UserRole.CUSTOMER_ADMIN,
        "tenant_info": UserTenantInfo(
            user_id="test-admin-001",
            tenant_id=TEST_TENANT_ID,
            user_role=UserRole.CUSTOMER_ADMIN,
            tenant_name=TEST_TENANT_NAME,
            tenant_slug=TEST_TENANT_SLUG,
        ),
    },
    "user": {
        "user_id": "test-user-001",
        "role": UserRole.CUSTOMER_USER,
        "tenant_info": UserTenantInfo(
            user_id="test-user-001",
            tenant_id=TEST_TENANT_ID,
            user_role=UserRole.CUSTOMER_USER,
            tenant_name=TEST_TENANT_NAME,
            tenant_slug=TEST_TENANT_SLUG,
        ),
    },
    "readonly": {
        "user_id": "test-readonly-001",
        "role": UserRole.TENANT_READONLY,
        "tenant_info": UserTenantInfo(
            user_id="test-readonly-001",
            tenant_id=TEST_TENANT_ID,
            user_role=UserRole.TENANT_READONLY,
            tenant_name=TEST_TENANT_NAME,
            tenant_slug=TEST_TENANT_SLUG,
        ),
    },
}

# Default user for most tests
DEFAULT_TEST_USER = TEST_USERS["admin"]

# Mock Authentication Factories


def create_mock_auth(user_config: dict, is_super_admin: bool = False):
    """
    Factory function to create mock auth dependencies.
    
    Args:
        user_config: User configuration dict from TEST_USERS
        is_super_admin: Whether this user should be a super admin
    
    Returns:
        Async function that returns AuthorizedUser
    """

    async def mock_auth():
        return AuthorizedUser(
            sub=user_config["user_id"],
            tenant_info=user_config["tenant_info"],
            is_super_admin=is_super_admin,
        )

    return mock_auth


# Session-Level Setup


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Session-level setup that runs once before all tests.
    
    Sets up:
    - Tenant cache with test users
    - Default auth dependency overrides
    - Any global test configuration
    """
    # Populate cache with all test users
    current_time = time.time()
    for user_key, user_config in TEST_USERS.items():
        _tenant_cache[user_config["user_id"]] = (
            user_config["tenant_info"],
            current_time,
        )

    # Set default auth overrides (using admin user)
    default_mock_auth = create_mock_auth(DEFAULT_TEST_USER)
    app.dependency_overrides[get_authorized_user] = default_mock_auth
    app.dependency_overrides[get_current_user] = default_mock_auth

    yield

    # Cleanup after all tests
    app.dependency_overrides.clear()
    _tenant_cache.clear()


# Test Clients


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Default test client using the admin user.
    
    Use this for most tests that don't need specific role testing.
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def admin_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as CUSTOMER_ADMIN"""
    mock_auth = create_mock_auth(TEST_USERS["admin"])
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    default_mock = create_mock_auth(DEFAULT_TEST_USER)
    app.dependency_overrides[get_authorized_user] = default_mock
    app.dependency_overrides[get_current_user] = default_mock


@pytest.fixture
def user_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as CUSTOMER_USER"""
    mock_auth = create_mock_auth(TEST_USERS["user"])
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    default_mock = create_mock_auth(DEFAULT_TEST_USER)
    app.dependency_overrides[get_authorized_user] = default_mock
    app.dependency_overrides[get_current_user] = default_mock


@pytest.fixture
def readonly_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as TENANT_READONLY"""
    mock_auth = create_mock_auth(TEST_USERS["readonly"])
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    default_mock = create_mock_auth(DEFAULT_TEST_USER)
    app.dependency_overrides[get_authorized_user] = default_mock
    app.dependency_overrides[get_current_user] = default_mock


@pytest.fixture
def super_admin_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as SUPER_ADMIN"""
    mock_auth = create_mock_auth(DEFAULT_TEST_USER, is_super_admin=True)
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    # Restore default
    default_mock = create_mock_auth(DEFAULT_TEST_USER)
    app.dependency_overrides[get_authorized_user] = default_mock
    app.dependency_overrides[get_current_user] = default_mock


@pytest.fixture
def unauthenticated_client() -> Generator[TestClient, None, None]:
    """
    Test client with NO authentication.
    """
    # Clear auth overrides
    app.dependency_overrides.pop(get_authorized_user, None)
    app.dependency_overrides.pop(get_current_user, None)

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    default_mock = create_mock_auth(DEFAULT_TEST_USER)
    app.dependency_overrides[get_authorized_user] = default_mock
    app.dependency_overrides[get_current_user] = default_mock

# Utility Fixtures

@pytest.fixture
def mock_user_info():
    """Provides access to test user configurations"""
    return TEST_USERS


@pytest.fixture
def auth_headers():
    """
    Standard auth headers for manual requests.
    
    The actual token value dont matter since were mocking auth,
    but it needs to be present for FastAPIs security scheme.
    """
    return {"Authorization": "Bearer test-token"}

def pytest_configure(config):
    """Pytest hook for additional configuration"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "auth: mark test as requiring authentication"
    )
    config.addinivalue_line(
        "markers", "admin_only: mark test as requiring admin role"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )