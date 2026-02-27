import pytest
import uuid
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.libs.tenant_models import (
    Tenant, TenantListResponse, TenantOverview,
    TenantMachinesResponse, Machine, UserTenantInfo
)

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"


def db_execute(db, query, *args):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(db.execute(query, *args))


def db_fetchrow(db, query, *args):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(db.fetchrow(query, *args))




class TestAdminDashboard:
    """Test suite for GET /admin/admin/dashboard endpoint"""

    def test_get_admin_dashboard_success(self, admin_client, mocker):
        mocker.patch("app.apis.admin.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=True)
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
        assert len(data["recent_tenants"]) == 1
        assert len(data["power_overview"]) == 1

    def test_get_admin_dashboard_with_period(self, admin_client, mocker):
        mocker.patch("app.apis.admin.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=True)
        mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[])
        mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock, return_value={
            "total_tenants": 0, "total_machines": 0, "total_active_tenants": 0
        })

        response = admin_client.get("/api/admin/admin/dashboard?period=24h")
        assert response.status_code == 200

    def test_get_admin_dashboard_not_super_admin(self, user_client, mocker):
        mocker.patch("app.apis.admin.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=False)

        response = user_client.get("/api/admin/admin/dashboard")
        assert response.status_code == 403

    def test_get_admin_dashboard_with_tenant_filter(self, admin_client, mocker):
        mocker.patch("app.apis.admin.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=True)
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


class TestAdminDashboardExport:
    """Test suite for GET /admin/admin/dashboard/export endpoint"""

    def test_export_dashboard_csv_success(self, admin_client, mocker):
        mocker.patch("app.apis.admin.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=True)
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

    def test_export_dashboard_csv_not_super_admin(self, user_client, mocker):
        mocker.patch("app.apis.admin.is_super_admin_with_auto_register", new_callable=AsyncMock, return_value=False)

        response = user_client.get("/api/admin/admin/dashboard/export")
        assert response.status_code == 403




class TestAdminListTenants:
    """Test suite for GET /admin/tenants endpoint"""

    def test_list_tenants_success(self, admin_client, db):
        response = admin_client.get("/api/admin/tenants")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 1
        assert any(t["id"] == TEST_TENANT_ID for t in data["tenants"])

    def test_list_tenants_with_pagination(self, admin_client, db):
        response = admin_client.get("/api/admin/tenants?limit=50&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "tenants" in data
        assert "total_count" in data

    def test_list_tenants_multiple(self, admin_client, db):
        tenant_id_2 = str(uuid.uuid4())
        db_execute(db,
            "INSERT INTO tenants (id, name, slug, active, settings, tenant_type, metadata) "
            "VALUES ($1, $2, $3, true, '{}', 'factory', '{}')",
            tenant_id_2, "Second Tenant", "second-tenant"
        )

        response = admin_client.get("/api/admin/tenants")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 2
        assert any(t["id"] == tenant_id_2 for t in data["tenants"])



class TestAdminCreateTenant:
    """Test suite for POST /admin/tenants endpoint"""

    def test_create_tenant_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        slug = f"new-tenant-{uuid.uuid4().hex[:8]}"
        response = admin_client.post("/api/admin/tenants", json={
            "name": "New Tenant",
            "slug": slug,
            "contact_email": "contact@newtenant.com"
        })

        assert response.status_code == 200
        assert response.json()["slug"] == slug

        row = db_fetchrow(db, "SELECT * FROM tenants WHERE slug = $1", slug)
        assert row is not None
        assert row["name"] == "New Tenant"

    def test_create_tenant_duplicate_slug(self, admin_client, db, mocker):
        """seed-tenant bruker slug 'test-tenant' — sender duplikat"""
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.post("/api/admin/tenants", json={
            "name": "Duplicate",
            "slug": "test-tenant",
            "contact_email": "dup@example.com"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_tenant_not_super_admin(self, user_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=False
        )

        response = user_client.post("/api/admin/tenants", json={
            "name": "New Tenant", "slug": "new-tenant", "contact_email": "x@x.com"
        })
        assert response.status_code == 403



class TestAdminGetTenant:
    """Test suite for GET /admin/tenants/{tenant_id} endpoint"""

    def test_get_tenant_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get(f"/api/admin/tenants/{TEST_TENANT_ID}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == TEST_TENANT_ID
        assert data["name"] == "Test Tenant"

    def test_get_tenant_not_found(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_tenant_invalid_id(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get("/api/admin/tenants/invalid-uuid")
        assert response.status_code == 400




class TestAdminUpdateTenant:
    """Test suite for PUT /admin/tenants/{tenant_id} endpoint"""

    def test_update_tenant_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        tenant_id = str(uuid.uuid4())
        db_execute(db,
            "INSERT INTO tenants (id, name, slug, active, settings, tenant_type, metadata) "
            "VALUES ($1, $2, $3, true, '{}', 'factory', '{}')",
            tenant_id, "Original Name", f"slug-{tenant_id[:8]}"
        )

        response = admin_client.put(
            f"/api/admin/tenants/{tenant_id}",
            json={"name": "Updated Tenant Name"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Updated Tenant Name"

        row = db_fetchrow(db, "SELECT name FROM tenants WHERE id = $1::uuid", tenant_id)
        assert row["name"] == "Updated Tenant Name"

    def test_update_tenant_not_found(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.put(f"/api/admin/tenants/{uuid.uuid4()}", json={"name": "X"})
        assert response.status_code == 404



class TestAdminTenantOverview:
    """Test suite for GET /admin/tenants/{tenant_id}/overview endpoint"""

    def test_get_tenant_overview_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get(f"/api/admin/tenants/{TEST_TENANT_ID}/overview")

        assert response.status_code == 200
        assert response.json()["tenant"]["id"] == TEST_TENANT_ID

    def test_get_tenant_overview_not_found(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}/overview")
        assert response.status_code == 404



class TestAdminTenantMachines:
    """Test suite for GET /admin/tenants/{tenant_id}/machines endpoint"""

    def test_get_tenant_machines_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        machine_id = str(uuid.uuid4())
        db_execute(db,
            "INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
            machine_id, TEST_TENANT_ID, "AABBCCDDEEFF0011", "Admin Test Machine"
        )

        response = admin_client.get(f"/api/admin/tenants/{TEST_TENANT_ID}/machines")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["machines"][0]["id"] == machine_id

    def test_get_tenant_machines_empty(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get(f"/api/admin/tenants/{TEST_TENANT_ID}/machines")

        assert response.status_code == 200
        assert response.json()["total_count"] == 0

    def test_get_tenant_machines_tenant_not_found(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}/machines")
        assert response.status_code == 404



class TestAdminCreateMachine:
    """Test suite for POST /admin/tenants/{tenant_id}/machines endpoint"""

    def test_create_machine_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.post(
            f"/api/admin/tenants/{TEST_TENANT_ID}/machines",
            json={"eui": "AABBCCDDEEFF1122", "name": "Admin Created Machine"}
        )

        assert response.status_code == 200
        assert response.json()["eui"] == "AABBCCDDEEFF1122"

        row = db_fetchrow(db, "SELECT * FROM machines WHERE eui = $1", "AABBCCDDEEFF1122")
        assert row is not None
        assert str(row["tenant_id"]) == TEST_TENANT_ID

    def test_create_machine_duplicate_eui(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        db_execute(db,
            "INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
            str(uuid.uuid4()), TEST_TENANT_ID, "DUPLICATE00001111", "Existing Machine"
        )

        response = admin_client.post(
            f"/api/admin/tenants/{TEST_TENANT_ID}/machines",
            json={"eui": "DUPLICATE00001111", "name": "New Machine"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_machine_tenant_not_found(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.post(
            f"/api/admin/tenants/{uuid.uuid4()}/machines",
            json={"eui": "DOESNOTMATTER111", "name": "X"}
        )
        assert response.status_code == 404


# TestAdminAddUserToTenant

class TestAdminAddUserToTenant:
    """Test suite for POST /admin/tenants/{tenant_id}/users endpoint"""

    def test_add_user_to_tenant_success(self, admin_client, db, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        new_user_id = f"new-user-{uuid.uuid4().hex[:8]}" #uuid required
        response = admin_client.post(
            f"/api/admin/tenants/{TEST_TENANT_ID}/users",
            json={"stack_user_id": new_user_id, "role": "customer_user"}
        )

        assert response.status_code == 200

        row = db_fetchrow(db, "SELECT * FROM tenant_users WHERE stack_user_id = $1", new_user_id)
        assert row is not None
        assert str(row["tenant_id"]) == TEST_TENANT_ID

    def test_add_user_to_tenant_not_found(self, admin_client, mocker):
        mocker.patch(
            "app.libs.super_admin_utils.is_super_admin_with_auto_register",
            new_callable=AsyncMock, return_value=True
        )

        response = admin_client.post(
            f"/api/admin/tenants/{uuid.uuid4()}/users",
            json={"stack_user_id": "some-user", "role": "customer_user"}
        )
        assert response.status_code == 404



# TestAdminMyTenant

class TestAdminMyTenant:
    """Test suite for GET /admin/my-tenant endpoint"""

    def test_get_my_tenant_info(self, admin_client, mocker, mock_tenant_info):
        mocker.patch(
            "app.apis.admin.get_user_tenant_info",
            new_callable=AsyncMock, return_value=mock_tenant_info
        )

        response = admin_client.get("/api/admin/my-tenant")

        assert response.status_code == 200
        data = response.json()
        assert str(data["tenant_id"]) == str(mock_tenant_info.tenant_id)

    def test_get_my_tenant_info_no_association(self, admin_client, mocker):
        mocker.patch(
            "app.apis.admin.get_user_tenant_info",
            new_callable=AsyncMock, return_value=None
        )

        response = admin_client.get("/api/admin/my-tenant")
        assert response.status_code == 200
        assert response.json() is None


# TestAdminDebugUserInfo

class TestAdminDebugUserInfo:
    """Test suite for GET /admin/debug/user-info endpoint"""

    def test_debug_user_info_success(self, admin_client, db, mocker, mock_tenant_info):
        mocker.patch(
            "app.apis.admin.get_user_tenant_info",
            new_callable=AsyncMock, return_value=mock_tenant_info
        )

        response = admin_client.get("/api/admin/debug/user-info")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-admin-001"
        assert data["is_super_admin"] is True