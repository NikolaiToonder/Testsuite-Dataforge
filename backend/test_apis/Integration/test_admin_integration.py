import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock

TEST_TENANT = "11111111-1111-1111-1111-111111111111"


def run(db, query, *args):
    return asyncio.get_event_loop().run_until_complete(db.execute(query, *args))

def fetchrow(db, query, *args):
    return asyncio.get_event_loop().run_until_complete(db.fetchrow(query, *args))

def patch_admin(mocker, value=True):
    mocker.patch("app.apis.admin.is_super_admin_with_auto_register",
        new_callable=AsyncMock, return_value=value)

def patch_lib_admin(mocker, value=True):
    mocker.patch("app.libs.super_admin_utils.is_super_admin_with_auto_register",
        new_callable=AsyncMock, return_value=value)

def dashboard_mocks(mocker, tenants=None, overview=None, stats=None):
    mocker.patch("app.apis.admin.get_recent_tenants", new_callable=AsyncMock, return_value=tenants or [])
    mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=overview or [])
    mocker.patch("app.apis.admin.get_dashboard_stats", new_callable=AsyncMock,
        return_value=stats or {"total_tenants": 0, "total_machines": 0, "total_active_tenants": 0})


class TestDashboard:

    def test_success(self, admin_client, mocker):
        patch_admin(mocker)
        dashboard_mocks(mocker,
            tenants=[{"id": "123", "name": "Test Testington", "slug": "UltraTEster",
                      "created_at": "2024-01-01T00:00:00", "active": True}],
            stats={"total_tenants": 10, "total_machines": 50, "total_active_tenants": 8}
        )
        res = admin_client.get("/api/admin/admin/dashboard")
        assert res.status_code == 200
        data = res.json()
        assert data["is_super_admin"] is True
        assert data["total_tenants"] == 10

    def test_forbidden_for_regular_user(self, user_client, mocker):
        patch_admin(mocker, value=False)
        assert user_client.get("/api/admin/admin/dashboard").status_code == 403

    def test_export_returns_csv(self, admin_client, mocker):
        patch_admin(mocker)
        mocker.patch("app.apis.admin.get_tenant_power_overview", new_callable=AsyncMock, return_value=[])
        res = admin_client.get("/api/admin/admin/dashboard/export")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]


class TestTenants:

    def test_list(self, admin_client, db):
        res = admin_client.get("/api/admin/tenants")
        assert res.status_code == 200
        data = res.json()
        assert data["total_count"] >= 1
        assert any(t["id"] == TEST_TENANT for t in data["tenants"])

    def test_create(self, admin_client, db, mocker):
        patch_lib_admin(mocker)
        slug = f"tenant-{uuid.uuid4().hex[:8]}"
        res = admin_client.post("/api/admin/tenants", json={
            "name": "Giga Testing", "slug": slug, "contact_email": "gigaTest@test.com"
        })

        assert res.status_code == 200
        assert fetchrow(db, "SELECT * FROM tenants WHERE slug = $1", slug) is not None

    def test_create_duplicate_slug_fails(self, admin_client, mocker):
        patch_lib_admin(mocker)
        res = admin_client.post("/api/admin/tenants", json={
            "name": "Dup", "slug": "test-tenant", "contact_email": "gigaTest@test.com"
        })
        assert res.status_code == 400

    def test_get(self, admin_client, mocker):
        patch_lib_admin(mocker)
        res = admin_client.get(f"/api/admin/tenants/{TEST_TENANT}")
        assert res.status_code == 200
        assert res.json()["id"] == TEST_TENANT

    def test_get_not_found(self, admin_client, mocker):
        patch_lib_admin(mocker)
        assert admin_client.get(f"/api/admin/tenants/{uuid.uuid4()}").status_code == 404

    def test_update(self, admin_client, db, mocker):
        patch_lib_admin(mocker)
        tid = str(uuid.uuid4())
        run(db,
            "INSERT INTO tenants (id, name, slug, active, settings, tenant_type, metadata) "
            "VALUES ($1, $2, $3, true, '{}', 'factory', '{}')",
            tid, "Old Name", f"slug-{tid[:8]}"
        )
        res = admin_client.put(f"/api/admin/tenants/{tid}", json={"name": "New Name"})
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"


class TestMachines:

    def test_list(self, admin_client, db, mocker):
        patch_lib_admin(mocker)
        mid = str(uuid.uuid4())
        run(db, "INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
            mid, TEST_TENANT, "AABBCCDDEEFF0011", "Test Machine")
        res = admin_client.get(f"/api/admin/tenants/{TEST_TENANT}/machines")
        assert res.status_code == 200
        assert res.json()["machines"][0]["id"] == mid

    def test_create(self, admin_client, db, mocker):
        patch_lib_admin(mocker)
        res = admin_client.post(f"/api/admin/tenants/{TEST_TENANT}/machines",
            json={"eui": "AABBCCDDEEFF1122", "name": "New Machine"})
        assert res.status_code == 200
        assert fetchrow(db, "SELECT * FROM machines WHERE eui = $1", "AABBCCDDEEFF1122") is not None

    def test_create_duplicate_eui_fails(self, admin_client, db, mocker):
        patch_lib_admin(mocker)
        run(db, "INSERT INTO machines (id, tenant_id, eui, name) VALUES ($1::uuid, $2::uuid, $3, $4)",
            str(uuid.uuid4()), TEST_TENANT, "DUPLICATE00001111", "Existing")
        res = admin_client.post(f"/api/admin/tenants/{TEST_TENANT}/machines",
            json={"eui": "DUPLICATE00001111", "name": "New"})
        assert res.status_code == 400


class TestUsers:

    def test_add_user_to_tenant(self, admin_client, db, mocker):
        patch_lib_admin(mocker)
        uid = f"user-{uuid.uuid4().hex[:8]}"
        res = admin_client.post(f"/api/admin/tenants/{TEST_TENANT}/users",
            json={"stack_user_id": uid, "role": "customer_user"})
        assert res.status_code == 200
        assert fetchrow(db, "SELECT * FROM tenant_users WHERE stack_user_id = $1", uid) is not None


class TestMyTenant:

    def test_returns_tenant_info(self, admin_client, mocker, mock_tenant_info):
        mocker.patch("app.apis.admin.get_user_tenant_info",
            new_callable=AsyncMock, return_value=mock_tenant_info)
        res = admin_client.get("/api/admin/my-tenant")
        assert res.status_code == 200
        assert str(res.json()["tenant_id"]) == str(mock_tenant_info.tenant_id)

    def test_returns_null_when_no_association(self, admin_client, mocker):
        mocker.patch("app.apis.admin.get_user_tenant_info",
            new_callable=AsyncMock, return_value=None)
        assert admin_client.get("/api/admin/my-tenant").json() is None