import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

TEST_TENANT = "11111111-1111-1111-1111-111111111111"


class TestRoleAccessOnRealRoutes:
    """Role enforcement tested against real app routes"""

    def test_customer_user_can_access_my_tenant(self, user_client):
        res = user_client.get("/api/admin/my-tenant")
        assert res.status_code == 200

    def test_readonly_can_access_my_tenant(self, readonly_client):
        res = readonly_client.get("/api/admin/my-tenant")
        assert res.status_code == 200

    def test_unauthenticated_blocked_from_my_tenant(self, unauthenticated_client):
        res = unauthenticated_client.get("/api/admin/my-tenant")
        assert res.status_code in (401, 422)

    def test_customer_user_can_list_machines(self, user_client):
        res = user_client.get("/api/customer/machines")
        assert res.status_code == 200

    def test_readonly_blocked_from_creating_machine(self, readonly_client):
        res = readonly_client.post("/api/customer/machines", json={"eui": "AABBCCDDEEFF0011", "name": "Test"})
        assert res.status_code == 403

    def test_unauthenticated_blocked_from_machines(self, unauthenticated_client):
        res = unauthenticated_client.get("/api/customer/machines")
        assert res.status_code in (401, 422)

    def test_customer_user_can_access_customer_tenant(self, user_client):
        res = user_client.get("/api/customer/my-tenant")
        assert res.status_code == 200


class TestSuperAdminRoutes:
    """Only super admins can access /api/admin/tenants and related routes."""

    def test_super_admin_can_list_tenants(self, admin_client):
        res = admin_client.get("/api/admin/tenants")
        assert res.status_code == 200

    def test_super_admin_can_get_tenant(self, admin_client):
        res = admin_client.get(f"/api/admin/tenants/{TEST_TENANT}")
        assert res.status_code == 200

    def test_regular_user_blocked_from_tenant_detail(self, user_client):
        res = user_client.get(f"/api/admin/tenants/{TEST_TENANT}")
        assert res.status_code == 403

    def test_super_admin_can_access_dashboard(self, admin_client, mocker):
        patch_admin(mocker)
        res = admin_client.get("/api/admin/admin/dashboard")
        assert res.status_code == 200

    def test_regular_user_blocked_from_dashboard(self, user_client, mocker):
        mocker.patch(
            "app.apis.admin.is_super_admin_with_auto_register",
            new_callable=AsyncMock,
            return_value=False,
        )
        res = user_client.get("/api/admin/admin/dashboard")
        assert res.status_code == 403

    def test_unauthenticated_blocked_from_tenant_list(self, unauthenticated_client):
        res = unauthenticated_client.get("/api/admin/tenants")
        assert res.status_code in (401, 422)


class TestSuperAdminActingAsTenant:

    def test_acting_as_tenant_header_accepted(self, admin_client, mocker):
        mocker.patch(
            "app.libs.auth.get_tenant_by_id",
            new_callable=AsyncMock,
            return_value=MagicMock(),
        )
        res = admin_client.get(
            "/api/admin/my-tenant",
            headers={"X-Acting-As-Tenant": TEST_TENANT},
        )
        assert res.status_code == 200

    def test_non_super_admin_acting_header_ignored(self, user_client):
        res = user_client.get(
            "/api/admin/my-tenant",
            headers={"X-Acting-As-Tenant": str(uuid.uuid4())},
        )
        assert res.status_code == 200

    def test_super_admin_invalid_acting_tenant_is_ignored(self, admin_client, mocker):
        mocker.patch(
            "app.libs.auth.get_tenant_by_id",
            new_callable=AsyncMock,
            return_value=None,
        )
        res = admin_client.get(
            "/api/admin/my-tenant",
            headers={"X-Acting-As-Tenant": TEST_TENANT},
        )
        assert res.status_code == 200


def patch_admin(mocker, value=True):
    mocker.patch(
        "app.apis.admin.is_super_admin_with_auto_register",
        new_callable=AsyncMock,
        return_value=value,
    ) 