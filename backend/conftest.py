import pytest
import os
import sys
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

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

# --- Global Fixtures ---
@pytest.fixture(autouse=True)
def global_db_blocker(setup_silent_db_mock):
    """Uses the service_mock logic to prevent real DB hits."""
    yield setup_silent_db_mock

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