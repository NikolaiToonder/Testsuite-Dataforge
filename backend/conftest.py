import pytest
import asyncio
import os
import sys
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

# --- Path Setup --- (may change later in the project)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../../dataforge/backend"))

if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

os.chdir(BACKEND_ROOT)

from main import app

# --- Mock imports ---

from test_mocks.auth_mocks import (
    TEST_USERS,
    admin_client,
    user_client,
    readonly_client,
    create_mock_auth
)
from test_mocks.data_mocks import (
    mock_tenant,
    mock_tenant_overview,
    mock_machine
)
from test_mocks.service_mocks import (
    setup_silent_db_mock,
    mock_db_row
)


# --- Testcontainer DB Fixtures ---

async def _init_test_db(url: str):
    """Initialize the test database: create schema only (empty tables)."""
    import asyncpg
    conn = await asyncpg.connect(url)
    try:
        schema_path = os.path.join(CURRENT_DIR, "test_schema.sql")
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
            test_tenant_id, "Test Tenant", "test-tenant",
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
                user_id, tenant_id, role,
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
    """Simple database connection for inserting/cleaning test data.

    Usage in tests:
        db.execute("INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
                   "aaaa...", "1111...", "ABCDEF1234567890", "My Machine")

    Data inserted into tables (except tenants, tenant_users, super_admins)
    is automatically cleaned up after each test.
    """
    import asyncpg

    # Create a new event loop for this fixture
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    conn = loop.run_until_complete(asyncpg.connect(db_url))
    
    # Clean BEFORE the test runs (in case of previous test failures)
    loop.run_until_complete(conn.execute(
        """
        DELETE FROM machines;
        DELETE FROM sensors;
        DELETE FROM gateways;
        DELETE FROM departments;
        """
    ))
    
    yield conn
    
    # Clean AFTER the test runs
    loop.run_until_complete(conn.execute(
        """
        DELETE FROM machines;
        DELETE FROM sensors;
        DELETE FROM gateways;
        DELETE FROM departments;
        """
    ))
    loop.run_until_complete(conn.close())
    loop.close()

# --- General Fixtures ---

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
