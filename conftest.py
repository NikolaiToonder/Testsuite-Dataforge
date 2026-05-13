import asyncio
import os
import sys
import uuid
from datetime import datetime
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from unittest.mock import AsyncMock, MagicMock

# --- Path Setup ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_BACKEND_ROOT = os.path.join(CURRENT_DIR, "backend")
APP_BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "dataforge", "backend"))

if APP_BACKEND_ROOT not in sys.path:
    sys.path.insert(0, APP_BACKEND_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

os.chdir(APP_BACKEND_ROOT)

from main import app
from app.libs.auth import get_current_user
from app.libs.tenant_models import Machine, Tenant, TenantOverview, UserRole, UserTenantInfo
from databutton_app.mw.auth_mw import AuthorizedUser, get_authorized_user


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


@pytest.fixture
def mock_tenant():
    """Reusable mock Tenant object"""
    return Tenant(
        id=uuid.UUID(TEST_TENANT_ID),
        name=TEST_TENANT_NAME,
        slug=TEST_TENANT_SLUG,
        contact_email="contact@innoveria.no",
        active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tenant_type="factory",
        settings={},
        metadata={},
    )


@pytest.fixture
def mock_tenant_overview(mock_tenant):
    """Reusable mock TenantOverview object"""
    return TenantOverview(
        tenant=mock_tenant,
        machine_count=5,
        active_machines=2,
        last_reading=None,
        total_readings_last_24h=100,
        average_power_kw=25.5,
    )


@pytest.fixture
def mock_machine(mock_tenant):
    """Reusable mock Machine object"""
    return Machine(
        id=uuid.uuid4(),
        tenant_id=mock_tenant.id,
        eui="1234567890ABCDEF",
        name="Test Machine",
        location="Floor 1",
        max_expected_amps=50.0,
        min_expected_amps=0.0,
        config={},
        active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def setup_silent_db_mock(mocker):
    """
    Ensures no test ever hits the real database,
    covering both pool-based and direct-connect patterns.
    """
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()
    mocker.patch(
        "app.libs.tenant_database.get_connection_pool",
        new_callable=AsyncMock,
        return_value=mock_pool,
    )
    mocker.patch("asyncpg.connect", return_value=mock_conn)
    yield mock_conn


@pytest.fixture
def mock_db_row():
    """
    Returns a factory function to create mock DB rows that support
    dictionary-style access (row['key']).

    Raises KeyError for missing keys — same behaviour as a real asyncpg
    Record — so tests fail loudly if the source code tries to access a
    key that was not set up in the mock.
    """

    def _create_row(data_dict: dict):
        row = MagicMock()

        row.__getitem__.side_effect = lambda key: data_dict[key]
        row.__contains__.side_effect = lambda key: key in data_dict
        row.get.side_effect = data_dict.get

        return row

    return _create_row


async def _init_test_db(url: str):
    """Initialize the test database: create schema only (empty tables)."""
    import asyncpg

    conn = await asyncpg.connect(url)
    try:
        schema_path = os.path.join(TEST_BACKEND_ROOT, "test_schema.sql")
        with open(schema_path, "r") as f:
            schema_sql = f.read()
        await conn.execute(schema_sql)

        # Insert a minimal test tenant (needed as FK target for tenant_users)
        test_tenant_id = "11111111-1111-1111-1111-111111111111"
        await conn.execute(
            """
            INSERT INTO tenants (id, name, slug, active, settings, tenant_type, metadata)
            VALUES ($1, $2, $3, true, '{}', 'factory', '{}')
            """,
            test_tenant_id,
            "Test Tenant",
            "test-tenant",
        )

        # Insert test users (matching auth_mocks.TEST_USERS)
        test_users = [
            ("test-admin-001", test_tenant_id, "customer_admin"),
            ("test-user-001", test_tenant_id, "customer_user"),
            ("test-readonly-001", test_tenant_id, "tenant_readonly"),
        ]
        for user_id, tenant_id, role in test_users:
            await conn.execute(
                "INSERT INTO tenant_users (stack_user_id, tenant_id, role) VALUES ($1, $2, $3)",
                user_id,
                tenant_id,
                role,
            )

        # Insert super_admin record for the admin test user
        await conn.execute(
            "INSERT INTO super_admins (user_id, active) VALUES ($1, true)",
            "test-admin-001",
        )
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container once for the entire test session."""
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session", autouse=True)
def db_url(postgres_container):
    """Build asyncpg-compatible URL and initialize empty schema."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    user = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname

    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    os.environ["DATABASE_URL"] = url

    asyncio.run(_init_test_db(url))

    return url


@pytest.fixture(autouse=True)
def reset_db_state():
    """Reset global connection pool and tenant cache before each test."""
    import app.libs.database as db_mod
    from app.libs.tenant_database import _tenant_cache

    db_mod._connection_pool = None
    _tenant_cache.clear()
    yield
    db_mod._connection_pool = None
    _tenant_cache.clear()


@pytest.fixture
def db(db_url):
    """Simple database connection for inserting/cleaning test data."""
    import asyncpg

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    conn = loop.run_until_complete(asyncpg.connect(db_url))

    loop.run_until_complete(
        conn.execute(
            """
        DELETE FROM machines;
        DELETE FROM sensors;
        DELETE FROM gateways;
        DELETE FROM departments;
        """
        )
    )

    yield conn

    loop.run_until_complete(
        conn.execute(
            """
        DELETE FROM machines;
        DELETE FROM sensors;
        DELETE FROM gateways;
        DELETE FROM departments;
        """
        )
    )
    loop.run_until_complete(conn.close())
    loop.close()


@pytest.fixture
def auth_headers():
    """Standard auth headers for manual requests."""
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def client(admin_client):
    """Generic client alias - defaults to admin."""
    return admin_client


@pytest.fixture
def unauthenticated_client():
    """Clean client with no overrides."""
    app.dependency_overrides.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_tenant_info():
    """Mock for get_user_tenant_info response."""
    mock = MagicMock()
    admin_info = TEST_USERS["admin"]["tenant_info"]
    mock.tenant_id = admin_info.tenant_id
    mock.tenant_name = admin_info.tenant_name
    mock.tenant_slug = admin_info.tenant_slug
    return mock


@pytest.fixture(autouse=True)
def mock_super_admin(mocker):
    mocker.patch(
        "app.libs.super_admin_utils.is_super_admin_with_auto_register",
        new_callable=AsyncMock,
        return_value=True,
    )