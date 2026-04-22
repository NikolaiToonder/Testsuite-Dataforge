import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from app.libs.tenant_models import (
    Tenant, TenantListResponse, TenantOverview,
    TenantMachinesResponse, Machine, UserTenantInfo,
    TenantType, UserRole
)


# Shared mock factories

def make_tenant(**kwargs) -> MagicMock:
    """Create a mock Tenant with good default values"""
    tenant = MagicMock(spec=Tenant)
    tenant.id = kwargs.get("id", uuid.uuid4())
    tenant.name = kwargs.get("name", "Test Tenant")
    tenant.slug = kwargs.get("slug", "test-tenant")
    tenant.active = kwargs.get("active", True)
    tenant.contact_email = kwargs.get("contact_email", None)
    tenant.tenant_type = kwargs.get("tenant_type", TenantType.FACTORY)
    tenant.created_at = kwargs.get("created_at", datetime(2024, 1, 1))
    tenant.updated_at = kwargs.get("updated_at", datetime(2024, 1, 1))
    return tenant


def make_machine(**kwargs) -> MagicMock:
    """Create a mock machine with some nice defaults"""
    machine = MagicMock(spec=Machine)
    machine.id = kwargs.get("id", uuid.uuid4())
    machine.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    machine.eui = kwargs.get("eui", "AABBCCDDEEFF0011")
    machine.name = kwargs.get("name", "Test Machine")
    machine.location = kwargs.get("location", "Floor 1")
    machine.active = kwargs.get("active", True)
    machine.created_at = kwargs.get("created_at", datetime(2024, 1, 1))
    machine.updated_at = kwargs.get("updated_at", datetime(2024, 1, 1))
    return machine


def make_tenant_overview(**kwargs) -> MagicMock:
    """Create a mock TenantOverview with some nice defaults"""
    overview = MagicMock(spec=TenantOverview)
    overview.tenant = kwargs.get("tenant", make_tenant())
    overview.machine_count = kwargs.get("machine_count", 3)
    overview.active_machines = kwargs.get("active_machines", 2)
    overview.last_reading = kwargs.get("last_reading", None)
    overview.total_readings_last_24h = kwargs.get("total_readings_last_24h", 100)
    overview.average_power_kw = kwargs.get("average_power_kw", 5.0)
    return overview


# TestAdminDashboard

class TestAdminDashboard:
    """Unit tests for GET /admin/admin/dashboard endpoint"""

    def test_get_admin_dashboard_success(self, admin_client, mocker):
        mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=[
            {"id": "123", "name": "Test Tenant", "slug": "test", "created_at": "2024-01-01T00:00:00", "active": True}
        ])
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[
            {
                "tenant_id": "123", "tenant_name": "Test Tenant", "tenant_slug": "test",
                "machine_count": 5, "total_readings": 100, "avg_power_kw": 10.5,
                "total_consumption_kw": 1050.0, "peak_power_kw": 15.0,
                "peak_machine_name": "Machine 1", "peak_timestamp": "2024-01-01T12:00:00",
                "has_data": True
            }
        ])
        mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock, return_value={
            "total_tenants": 10, "total_machines": 50, "total_active_tenants": 8
        })

        response = admin_client.get("/api/admin/admin/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-admin-001"
        assert data["is_super_admin"] is True
        assert data["total_tenants"] == 10
        assert data["total_machines"] == 50
        assert len(data["recent_tenants"]) == 1
        assert len(data["power_overview"]) == 1

    def test_get_admin_dashboard_empty_data(self, admin_client, mocker):
        mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock, return_value={
            "total_tenants": 0, "total_machines": 0, "total_active_tenants": 0
        })

        response = admin_client.get("/api/admin/admin/dashboard")

        assert response.status_code == 200
        data = response.json()
        assert data["total_tenants"] == 0
        assert data["recent_tenants"] == []
        assert data["power_overview"] == []

    def test_get_admin_dashboard_period_24h(self, admin_client, mocker):
        """Dashboard accepts period=24h"""

        mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock, return_value={
            "total_tenants": 0, "total_machines": 0, "total_active_tenants": 0
        })

        response = admin_client.get("/api/admin/admin/dashboard?period=24h")
        assert response.status_code == 200

    def test_get_admin_dashboard_period_30d(self, admin_client, mocker):
        """Dashboard aksepterer period=30d"""
        mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock, return_value={
            "total_tenants": 0, "total_machines": 0, "total_active_tenants": 0
        })

        response = admin_client.get("/api/admin/admin/dashboard?period=30d")
        assert response.status_code == 200

    def test_get_admin_dashboard_invalid_period(self, admin_client, mocker):
        """Dashboard rejects invalid periods"""
        response = admin_client.get("/api/admin/admin/dashboard?period=invalid")
        assert response.status_code == 422

    def test_get_admin_dashboard_not_super_admin(self, user_client, mocker):
        """Non-super-admin gets 403 (no permissions)"""

        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=False
        )

        response = user_client.get("/api/admin/admin/dashboard")
        assert response.status_code == 403

    def test_get_admin_dashboard_with_tenant_filter(self, admin_client, mocker):
        """Dashboard accepts X-Acting-As-Tenant header"""

        mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock, return_value={
            "total_tenants": 1, "total_machines": 5, "total_active_tenants": 1
        })

        response = admin_client.get(
            "/api/admin/admin/dashboard",
            headers={"X-Acting-As-Tenant": str(uuid.uuid4())}
        )
        assert response.status_code == 200


# TestAdminDashboardExport

class TestAdminDashboardExport:
    """Unit tests for GET /admin/admin/dashboard/export endpoint"""

    def test_export_csv_success(self, admin_client, mocker):
        """CSV-eksport returns correct content-type og attachment header"""

        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[
            {
                "tenant_id": "123", "tenant_name": "Test Tenant", "tenant_slug": "test",
                "machine_count": 5, "total_readings": 100, "avg_power_kw": 10.5,
                "total_consumption_kw": 1050.0, "peak_power_kw": 15.0,
                "peak_machine_name": "Machine 1", "peak_timestamp": "2024-01-01T12:00:00",
                "has_data": True
            }
        ])

        response = admin_client.get("/api/admin/admin/dashboard/export")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]


# TestAdminListTenants


class TestAdminListTenants:
    """Unit tests for GET /admin/tenants endpoint"""

    def test_list_tenants_success(self, admin_client, mocker):
        """Returns list with tenants and total_count"""
        tenant = make_tenant()
        mocker.patch("app.apis.admin.list_accessible_tenants", new_callable=AsyncMock, return_value=([tenant], 1))

        response = admin_client.get("/api/admin/tenants")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["tenants"]) == 1

    def test_list_tenants_empty(self, admin_client, mocker):
        """Test for empty tenant list"""

        mocker.patch("app.apis.admin.list_accessible_tenants", new_callable=AsyncMock, return_value=([], 0))

        response = admin_client.get("/api/admin/tenants")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["tenants"] == []

    def test_list_tenants_multiple(self, admin_client, mocker):
        """Check if multiple tenants returns correctly"""

        tenants = [make_tenant(name=f"Tenant {i}") for i in range(3)]
        mocker.patch("app.apis.admin.list_accessible_tenants", new_callable=AsyncMock, return_value=(tenants, 3))

        response = admin_client.get("/api/admin/tenants")

        assert response.status_code == 200
        assert response.json()["total_count"] == 3
        assert len(response.json()["tenants"]) == 3


# TestAdminCreateTenant

class TestAdminCreateTenant:
    """Unit tests for POST /admin/tenants endpoint"""

    def test_create_tenant_success(self, admin_client, mocker):
        """Can create new tenant"""

        tenant = make_tenant(name="New Tenant", slug="new-tenant")
        mocker.patch("app.apis.admin.get_tenant_by_slug", new_callable=AsyncMock, return_value=None)
        mocker.patch("app.apis.admin.create_tenant", new_callable=AsyncMock, return_value=tenant)

        response = admin_client.post("/api/admin/tenants", json={
            "name": "New Tenant",
            "slug": "new-tenant",
            "contact_email": "contact@newtenant.com"
        })

        assert response.status_code == 200
        assert response.json()["id"] == str(tenant.id)

    def test_create_tenant_duplicate_slug(self, admin_client, mocker):
        """Duplicate entries give 400"""

        existing = make_tenant(slug="existing-slug")
        mocker.patch("app.apis.admin.get_tenant_by_slug", new_callable=AsyncMock, return_value=existing)

        response = admin_client.post("/api/admin/tenants", json={
            "name": "New Tenant",
            "slug": "existing-slug",
            "contact_email": "x@x.com"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_tenant_not_super_admin(self, user_client, mocker):
        """Non-super admin gets permission denied"""

        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=False
        )

        response = user_client.post("/api/admin/tenants", json={
            "name": "New Tenant", "slug": "new-tenant", "contact_email": "x@x.com"
        })
        assert response.status_code == 403



# TestAdminGetTenant

class TestAdminGetTenant:
    """Unit tests for GET /admin/tenants/{tenant_id} endpoint"""

    def test_get_tenant_success(self, admin_client, mocker):
        """Found tenant returns correct ID"""

        tenant = make_tenant()
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)

        response = admin_client.get(f"/api/admin/tenants/{tenant.id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(tenant.id)

    def test_get_tenant_not_found(self, admin_client, mocker):
        """Non-existing tenant returns 404"""

        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=None)

        response = admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_tenant_invalid_uuid(self, admin_client):
        """Invalid UUID gets 400"""

        response = admin_client.get("/api/admin/tenants/not-a-uuid")
        assert response.status_code == 400

    def test_get_tenant_calls_correct_id(self, admin_client, mocker):
        """Tests if the request UUID is handled correctly"""

        tenant = make_tenant()
        mock_get = mocker.patch(
            "app.apis.admin.get_tenant_by_id",
            new_callable=AsyncMock, return_value=tenant
        )

        admin_client.get(f"/api/admin/tenants/{tenant.id}")

        mock_get.assert_called_once_with(tenant.id)



# TestAdminUpdateTenant

class TestAdminUpdateTenant:
    """Unit tests for PUT /admin/tenants/{tenant_id} endpoint"""

    def test_update_tenant_success(self, admin_client, mocker):
        """Updated tenant returns correctly"""
        tenant = make_tenant(name="Updated Name")
        mocker.patch("app.apis.admin.update_tenant", new_callable=AsyncMock, return_value=tenant)

        response = admin_client.put(f"/api/admin/tenants/{tenant.id}", json={"name": "Updated Name"})

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_update_tenant_not_found(self, admin_client, mocker):
        """Non-existing tenant gets 404"""

        mocker.patch("app.apis.admin.update_tenant", new_callable=AsyncMock, return_value=None)

        response = admin_client.put(f"/api/admin/tenants/{uuid.uuid4()}", json={"name": "X"})
        assert response.status_code == 404

    def test_update_tenant_invalid_uuid(self, admin_client):
        """Invalid uuid gets 400"""
        response = admin_client.put("/api/admin/tenants/not-a-uuid", json={"name": "X"})
        assert response.status_code == 400


# TestAdminTenantOverview

class TestAdminTenantOverview:
    """Unit tests for GET /admin/tenants/{tenant_id}/overview endpoint"""

    def test_get_overview_success(self, admin_client, mocker):
        """Overview returns with correct UUID"""

        overview = make_tenant_overview()
        mocker.patch("app.apis.admin.get_tenant_overview", new_callable=AsyncMock, return_value=overview)

        response = admin_client.get(f"/api/admin/tenants/{overview.tenant.id}/overview")

        assert response.status_code == 200
        assert response.json()["tenant"]["id"] == str(overview.tenant.id)

    def test_get_overview_not_found(self, admin_client, mocker):
        """Non-existing tenant gets 404"""

        mocker.patch("app.apis.admin.get_tenant_overview", new_callable=AsyncMock, return_value=None)

        response = admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}/overview")
        assert response.status_code == 404

    def test_get_overview_machine_count(self, admin_client, mocker):
        """machine_count from overview is correct"""

        overview = make_tenant_overview(machine_count=7)
        mocker.patch("app.apis.admin.get_tenant_overview", new_callable=AsyncMock, return_value=overview)

        response = admin_client.get(f"/api/admin/tenants/{overview.tenant.id}/overview")

        assert response.json()["machine_count"] == 7


# TestAdminTenantMachines

class TestAdminTenantMachines:
    """Unit tests for GET /admin/tenants/{tenant_id}/machines endpoint"""

    def test_get_machines_success(self, admin_client, mocker):
        """Machines from tenant returns with correct total_count"""

        tenant = make_tenant()
        machines = [make_machine(tenant_id=tenant.id) for _ in range(3)]
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)
        mocker.patch("app.apis.admin.get_tenant_machines", new_callable=AsyncMock, return_value=machines)

        response = admin_client.get(f"/api/admin/tenants/{tenant.id}/machines")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["machines"]) == 3

    def test_get_machines_empty(self, admin_client, mocker):
        """Tenant without machine returns empty list"""

        tenant = make_tenant()
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)
        mocker.patch("app.apis.admin.get_tenant_machines", new_callable=AsyncMock, return_value=[])

        response = admin_client.get(f"/api/admin/tenants/{tenant.id}/machines")

        assert response.status_code == 200
        assert response.json()["total_count"] == 0

    def test_get_machines_tenant_not_found(self, admin_client, mocker):
        """Non-existing tenant gets 404"""

        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=None)

        response = admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}/machines")
        assert response.status_code == 404



# TestAdminCreateMachine


class TestAdminCreateMachine:
    """Unit tests for POST /admin/tenants/{tenant_id}/machines endpoint"""

    def test_create_machine_success(self, admin_client, mocker):
        """New machine can be created"""

        tenant = make_tenant()
        machine = make_machine(tenant_id=tenant.id, eui="AABBCCDDEEFF1122")
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)
        mocker.patch("app.apis.admin.get_machine_by_eui", new_callable=AsyncMock, return_value=None)
        mocker.patch("app.apis.admin.create_machine", new_callable=AsyncMock, return_value=machine)

        response = admin_client.post(
            f"/api/admin/tenants/{tenant.id}/machines",
            json={"eui": "AABBCCDDEEFF1122", "name": "New Machine"}
        )

        assert response.status_code == 200
        assert response.json()["eui"] == "AABBCCDDEEFF1122"

    def test_create_machine_duplicate_eui(self, admin_client, mocker):
        """Duplicate EUI gets a 404"""

        tenant = make_tenant()
        existing = make_machine(eui="DUPLICATE00001111")
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)
        mocker.patch("app.apis.admin.get_machine_by_eui", new_callable=AsyncMock, return_value=existing)

        response = admin_client.post(
            f"/api/admin/tenants/{tenant.id}/machines",
            json={"eui": "DUPLICATE00001111", "name": "New Machine"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_machine_tenant_not_found(self, admin_client, mocker):
        """Non-existing tenant gets 404"""

        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=None)

        response = admin_client.post(
            f"/api/admin/tenants/{uuid.uuid4()}/machines",
            json={"eui": "AABBCCDDEEFF1122", "name": "X"}
        )
        assert response.status_code == 404

    def test_create_machine_does_not_call_create_on_duplicate(self, admin_client, mocker):
        """create_machine should not be called if EUI already exists"""
        
        tenant = make_tenant()
        existing = make_machine(eui="DUPLICATE00001111")
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)
        mocker.patch("app.apis.admin.get_machine_by_eui", new_callable=AsyncMock, return_value=existing)
        mock_create = mocker.patch("app.apis.admin.create_machine", new_callable=AsyncMock)

        admin_client.post(
            f"/api/admin/tenants/{tenant.id}/machines",
            json={"eui": "DUPLICATE00001111", "name": "X"}
        )

        mock_create.assert_not_called()


# TestAdminAddUserToTenant

class TestAdminAddUserToTenant:
    """Unit tests for POST /admin/tenants/{tenant_id}/users endpoint"""

    def test_add_user_success(self, admin_client, mocker):
        """User gets added to tenant and returns"""

        tenant = make_tenant()
        tenant_user = MagicMock()
        tenant_user.id = uuid.uuid4()
        tenant_user.stack_user_id = "new-user-123"
        tenant_user.tenant_id = tenant.id
        tenant_user.role = UserRole.CUSTOMER_USER
        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=tenant)
        mocker.patch("app.apis.admin.create_tenant_user", new_callable=AsyncMock, return_value=tenant_user)

        response = admin_client.post(
            f"/api/admin/tenants/{tenant.id}/users",
            json={"stack_user_id": "new-user-123", "role": "customer_user"}
        )

        assert response.status_code == 200

    def test_add_user_tenant_not_found(self, admin_client, mocker):
        """Non existing tenant gets 404"""

        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=None)

        response = admin_client.post(
            f"/api/admin/tenants/{uuid.uuid4()}/users",
            json={"stack_user_id": "some-user", "role": "customer_user"}
        )
        assert response.status_code == 404

    def test_add_user_does_not_create_on_missing_tenant(self, admin_client, mocker):
        """create_tenant_user  should not be called if tenant doesnt exist"""

        mocker.patch("app.apis.admin.get_tenant_by_id", new_callable=AsyncMock, return_value=None)
        mock_create = mocker.patch("app.apis.admin.create_tenant_user", new_callable=AsyncMock)

        admin_client.post(
            f"/api/admin/tenants/{uuid.uuid4()}/users",
            json={"stack_user_id": "some-user", "role": "customer_user"}
        )

        mock_create.assert_not_called()


# TestAdminMyTenant

class TestAdminMyTenant:
    """Unit tests for GET /admin/my-tenant endpoint"""

    def test_get_my_tenant_info(self, admin_client, mocker, mock_tenant_info):
        """Logged in users gets correct tenant info"""

        mocker.patch("app.apis.admin.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)

        response = admin_client.get("/api/admin/my-tenant")

        assert response.status_code == 200
        assert str(response.json()["tenant_id"]) == str(mock_tenant_info.tenant_id)

    def test_get_my_tenant_info_no_association(self, admin_client, mocker):
        """User without tenant gets None"""

        mocker.patch("app.apis.admin.get_user_tenant_info", new_callable=AsyncMock, return_value=None)

        response = admin_client.get("/api/admin/my-tenant")

        assert response.status_code == 200
        assert response.json() is None


# TestAdminDebugUserInfo

class TestAdminDebugUserInfo:
    """Unit tests for GET /admin/debug/user-info endpoint"""

    def test_debug_user_info_super_admin(self, admin_client, mocker, mock_tenant_info):
        """Super admin gets is_super_admin=True in response"""
        mocker.patch("app.apis.admin.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.admin.is_super_admin", new_callable=AsyncMock, return_value=True)

        response = admin_client.get("/api/admin/debug/user-info")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-admin-001"
        assert data["is_super_admin"] is True

    def test_debug_user_info_not_super_admin(self, admin_client, mocker, mock_tenant_info):
        """Normal user gets is_super_admin=False in response"""
        
        mocker.patch("app.apis.admin.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        mocker.patch("app.apis.admin.is_super_admin", new_callable=AsyncMock, return_value=False)

        response = admin_client.get("/api/admin/debug/user-info")

        assert response.status_code == 200
        assert response.json()["is_super_admin"] is False

    def test_debug_user_info_no_tenant(self, admin_client, mocker):
        """User without tenant gets None in user info"""

        mocker.patch("app.apis.admin.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        mocker.patch("app.apis.admin.is_super_admin", new_callable=AsyncMock, return_value=False)

        response = admin_client.get("/api/admin/debug/user-info")

        assert response.status_code == 200
        assert response.json()["tenant_info"] is None