import pytest
from typing import Generator
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from app.libs.tenant_models import UserRole, UserTenantInfo
from databutton_app.mw.auth_mw import AuthorizedUser

from main import app
from databutton_app.mw.auth_mw import get_authorized_user
from app.libs.auth import get_current_user

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_TENANT_NAME = "Innoveria AS"
TEST_TENANT_SLUG = "innoveria"

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

DEFAULT_TEST_USER = TEST_USERS["admin"]


def create_mock_auth(user_config: dict, is_super_admin: bool = False):
    """Creates an async dependency override for FastAPI auth."""
    async def mock_auth():
        return AuthorizedUser(
            sub=user_config["user_id"],
            tenant_info=user_config["tenant_info"],
            is_super_admin=is_super_admin,
        )
    return mock_auth


@pytest.fixture
def admin_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as CUSTOMER_ADMIN"""
    mock_auth = create_mock_auth(TEST_USERS["admin"])
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def user_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as CUSTOMER_USER"""
    mock_auth = create_mock_auth(TEST_USERS["user"])
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def readonly_client() -> Generator[TestClient, None, None]:
    """Test client authenticated as TENANT_READONLY"""
    mock_auth = create_mock_auth(TEST_USERS["readonly"])
    app.dependency_overrides[get_authorized_user] = mock_auth
    app.dependency_overrides[get_current_user] = mock_auth

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()

