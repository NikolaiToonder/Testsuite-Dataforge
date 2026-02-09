import pytest
import uuid
from datetime import datetime
from app.libs.tenant_models import Tenant, TenantOverview, Machine

# Constants
TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"
TEST_TENANT_NAME = "Innoveria AS"
TEST_TENANT_SLUG = "innoveria"


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
        metadata={}
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
        average_power_kw=25.5
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
        updated_at=datetime.now()
    )