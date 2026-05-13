import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"


def _import_user_invitations_module():
    return __import__("app.apis.user_invitations", fromlist=["*"])


@pytest.fixture
def mock_tx():
    """Mock asyncpg transaction async context manager: async with conn.transaction():"""
    tx_cm = AsyncMock()
    tx_cm.__aenter__ = AsyncMock(return_value=None)
    tx_cm.__aexit__ = AsyncMock(return_value=None)
    return tx_cm


@pytest.fixture
def fake_user_factory():
    """
    Return a factory that produces user objects matching what app.apis.user_invitations expects:
      - sub
      - tenant_id (str UUID)
      - user_role (str)
      - can_invite_users() -> bool
    """

    class FakeUser:
        def __init__(self, sub: str, tenant_id: str | None, user_role: str):
            self.sub = sub
            self.tenant_id = tenant_id
            self.user_role = user_role

        def can_invite_users(self) -> bool:
            # Your endpoint treats "customer_admin" (and "super_admin") as inviters.
            return self.user_role in ("customer_admin", "super_admin")

    def _make(role: str, tenant_id: str | None = TEST_TENANT_ID, sub: str = "test-user"):
        return FakeUser(sub=sub, tenant_id=tenant_id, user_role=role)

    return _make


@pytest.fixture
def override_current_user(admin_client):
    """
    Helper to override the dependency that the router uses: get_current_user (from app.libs.auth).
    Usage:
        with override_current_user(mod, fake_user):
            ...
    """
    app = admin_client.app

    class _Ctx:
        def __init__(self, mod, user_obj):
            self.mod = mod
            self.user_obj = user_obj

        def __enter__(self):
            async def _override():
                return self.user_obj

            app.dependency_overrides[self.mod.get_current_user] = _override
            return self

        def __exit__(self, exc_type, exc, tb):
            app.dependency_overrides.pop(self.mod.get_current_user, None)

    return _Ctx


# --------------------------------------------------------------------------------------
# INVITE USER
# --------------------------------------------------------------------------------------

class TestInviteUser:
    def test_invite_user_forbidden_if_not_admin(self, admin_client, override_current_user, fake_user_factory):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_user")

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/invite",
                json={"email": "a@b.com", "role": "customer_user"},
            )

        assert response.status_code == 403

    def test_invite_user_invalid_role(self, admin_client, override_current_user, fake_user_factory):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/invite",
                json={"email": "test@example.com", "role": "super_admin"},
            )

        assert response.status_code == 400

    def test_invite_user_missing_tenant_id(self, admin_client, override_current_user, fake_user_factory):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin", tenant_id=None)

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/invite",
                json={"email": "test@example.com", "role": "customer_user"},
            )

        assert response.status_code == 400

    def test_invite_user_creates_new_invitation(
        self,
        admin_client,
        override_current_user,
        fake_user_factory,
        mock_db_row,
        setup_silent_db_mock,
        mocker,
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        tenant_row = mock_db_row({"name": "Acme"})
        created_row = mock_db_row({"id": uuid.uuid4(), "created_at": datetime(2024, 1, 1, 12, 0, 0)})

        # Flow:
        # 1) tenant name lookup
        # 2) existing invitation check -> None
        # 3) member check -> None
        # 4) insert -> created_row
        conn.fetchrow = AsyncMock(side_effect=[tenant_row, None, None, created_row])
        conn.execute = AsyncMock()
        conn.close = AsyncMock()

        send_email = AsyncMock(return_value=True)
        mocker.patch.object(mod, "send_invitation_email", send_email)

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/invite",
                json={"email": "newuser@example.com", "role": "customer_user"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "invitation_id" in data
        assert "invitation_url" in data
        assert send_email.called is True

    def test_invite_user_existing_active_invitation_updates(
        self,
        admin_client,
        override_current_user,
        fake_user_factory,
        mock_db_row,
        setup_silent_db_mock,
        mocker,
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        existing_id = uuid.uuid4()

        tenant_row = mock_db_row({"name": "Acme"})
        existing_inv = mock_db_row({"id": existing_id, "used_at": None})
        updated_inv = mock_db_row({"id": existing_id, "created_at": datetime(2024, 1, 1, 12, 0, 0)})
        token_row = mock_db_row({"invitation_token": "tok-123"})

        # Flow:
        # 1) tenant lookup
        # 2) existing invitation check -> existing_inv
        # 3) update invitation -> updated_inv
        # 4) token lookup -> token_row
        conn.fetchrow = AsyncMock(side_effect=[tenant_row, existing_inv, updated_inv, token_row])
        conn.execute = AsyncMock()
        conn.close = AsyncMock()

        send_email = AsyncMock(return_value=True)
        mocker.patch.object(mod, "send_invitation_email", send_email)

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/invite",
                json={"email": "existing@example.com", "role": "customer_user"},
            )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert send_email.called is True

    def test_invite_user_existing_member_returns_400(
        self,
        admin_client,
        override_current_user,
        fake_user_factory,
        mock_db_row,
        setup_silent_db_mock,
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        tenant_row = mock_db_row({"name": "Acme"})
        member_row = mock_db_row({"id": uuid.uuid4()})

        # Flow:
        # 1) tenant lookup
        # 2) existing invitation -> None
        # 3) member check -> member_row
        conn.fetchrow = AsyncMock(side_effect=[tenant_row, None, member_row])
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/invite",
                json={"email": "member@example.com", "role": "customer_user"},
            )

        assert response.status_code == 400


# --------------------------------------------------------------------------------------
# LIST INVITATIONS
# --------------------------------------------------------------------------------------

class TestListInvitations:
    def test_list_invitations_forbidden_if_not_admin(self, admin_client, override_current_user, fake_user_factory):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_user")

        with override_current_user(mod, user):
            response = admin_client.get("/api/user-invitations/")

        assert response.status_code == 403

    def test_list_invitations_active_only_default(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        rows = [
            mock_db_row(
                {
                    "id": uuid.uuid4(),
                    "tenant_id": uuid.UUID(TEST_TENANT_ID),
                    "invited_by": "stack|inviter",
                    "email": "a@example.com",
                    "role": "customer_user",
                    "invitation_token": "tok1",
                    "expires_at": datetime.utcnow() + timedelta(days=3),
                    "used_at": None,
                    "used_by": None,
                    "created_at": datetime(2024, 1, 1),
                    "updated_at": datetime(2024, 1, 1),
                }
            )
        ]
        conn.fetch = AsyncMock(return_value=rows)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.get("/api/user-invitations/")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["invitations"][0]["email"] == "a@example.com"

    def test_list_invitations_include_all(
        self, admin_client, override_current_user, fake_user_factory, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        conn.fetch = AsyncMock(return_value=[])
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.get("/api/user-invitations/?active_only=false")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert data["invitations"] == []


# --------------------------------------------------------------------------------------
# ACCEPT INVITATION
# --------------------------------------------------------------------------------------

class TestAcceptInvitation:
    def test_accept_invitation_invalid_token(self, admin_client, override_current_user, fake_user_factory, setup_silent_db_mock):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        conn.fetchrow = AsyncMock(return_value=None)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/accept",
                json={"invitation_token": "bad-token"},
            )

        assert response.status_code == 400

    def test_accept_invitation_already_member(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        invitation_row = mock_db_row(
            {"id": uuid.uuid4(), "tenant_id": uuid.UUID(TEST_TENANT_ID), "role": "customer_user"}
        )
        member_row = mock_db_row({"id": uuid.uuid4()})

        conn.fetchrow = AsyncMock(side_effect=[invitation_row, member_row])
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/accept",
                json={"invitation_token": "tok"},
            )

        assert response.status_code == 400

    def test_accept_invitation_success(
        self,
        admin_client,
        override_current_user,
        fake_user_factory,
        mock_db_row,
        setup_silent_db_mock,
        mock_tx,
        mocker,
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin", sub="accepting-user")
        conn = setup_silent_db_mock

        inv_id = uuid.uuid4()
        invitation_row = mock_db_row(
            {"id": inv_id, "tenant_id": uuid.UUID(TEST_TENANT_ID), "role": "customer_user"}
        )
        user_insert_row = mock_db_row({"id": uuid.uuid4()})

        # 1) invitation lookup
        # 2) member check -> None
        # 3) insert tenant_users -> user_insert_row
        conn.fetchrow = AsyncMock(side_effect=[invitation_row, None, user_insert_row])
        conn.execute = AsyncMock()
        conn.close = AsyncMock()

        conn.transaction = mocker.MagicMock(return_value=mock_tx)

        with override_current_user(mod, user):
            response = admin_client.post(
                "/api/user-invitations/accept",
                json={"invitation_token": "tok"},
            )

        assert response.status_code == 200
        assert response.json()["success"] is True
        assert conn.execute.called is True


# --------------------------------------------------------------------------------------
# CANCEL INVITATION
# --------------------------------------------------------------------------------------

class TestCancelInvitation:
    def test_cancel_invitation_forbidden_if_not_admin(self, admin_client, override_current_user, fake_user_factory):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_user")

        with override_current_user(mod, user):
            response = admin_client.delete(f"/api/user-invitations/{uuid.uuid4()}")

        assert response.status_code == 403

    def test_cancel_invitation_not_found(
        self, admin_client, override_current_user, fake_user_factory, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        conn.fetchrow = AsyncMock(return_value=None)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.delete(f"/api/user-invitations/{uuid.uuid4()}")

        assert response.status_code == 404

    def test_cancel_invitation_success(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        conn.fetchrow = AsyncMock(return_value=mock_db_row({"id": uuid.uuid4()}))
        conn.execute = AsyncMock()
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.delete(f"/api/user-invitations/{uuid.uuid4()}")

        assert response.status_code == 200
        assert response.json()["success"] is True


# --------------------------------------------------------------------------------------
# LIST TENANT USERS
# --------------------------------------------------------------------------------------

class TestListTenantUsers:
    def test_list_tenant_users_user_not_associated(
        self, admin_client, override_current_user, fake_user_factory, mocker
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")

        mocker.patch.object(mod, "get_user_tenant_info", new=AsyncMock(return_value=None))

        with override_current_user(mod, user):
            response = admin_client.get("/api/user-invitations/users")

        assert response.status_code == 403

    def test_list_tenant_users_success(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock, mocker
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        mocker.patch.object(mod, "get_user_tenant_info", new=AsyncMock(return_value={"tenant_id": TEST_TENANT_ID}))

        rows = [
            mock_db_row(
                {
                    "id": uuid.uuid4(),
                    "email": "u@example.com",
                    "display_name": "User",
                    "role": "customer_user",
                    "joined_at": datetime(2024, 1, 1, 10, 0, 0),
                    "is_active": True,
                }
            )
        ]
        conn.fetch = AsyncMock(return_value=rows)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.get("/api/user-invitations/users")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["users"][0]["email"] == "u@example.com"


# --------------------------------------------------------------------------------------
# UPDATE TENANT USER
# --------------------------------------------------------------------------------------

class TestUpdateTenantUser:
    def test_update_tenant_user_forbidden_if_not_admin(self, admin_client, override_current_user, fake_user_factory):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_user")

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={"role": "customer_user"},
            )

        assert response.status_code == 403

    def test_update_tenant_user_not_found(
        self, admin_client, override_current_user, fake_user_factory, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        conn.fetchrow = AsyncMock(return_value=None)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={"role": "customer_user"},
            )

        assert response.status_code == 404

    def test_update_tenant_user_customer_admin_cannot_edit_other_tenant(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        row = mock_db_row({"tenant_id": uuid.uuid4(), "id": uuid.uuid4(), "role": "customer_user", "active": True})
        conn.fetchrow = AsyncMock(return_value=row)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={"active": False},
            )

        assert response.status_code == 403

    def test_update_tenant_user_invalid_role_customer_admin(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        row = mock_db_row(
            {"tenant_id": uuid.UUID(TEST_TENANT_ID), "id": uuid.uuid4(), "role": "customer_user", "active": True}
        )
        conn.fetchrow = AsyncMock(return_value=row)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={"role": "super_admin"},
            )

        assert response.status_code == 400

    def test_update_tenant_user_no_fields(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        row = mock_db_row(
            {"tenant_id": uuid.UUID(TEST_TENANT_ID), "id": uuid.uuid4(), "role": "customer_user", "active": True}
        )
        conn.fetchrow = AsyncMock(return_value=row)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={},
            )

        assert response.status_code == 400

    def test_update_tenant_user_success_role_and_active(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")
        conn = setup_silent_db_mock

        check_row = mock_db_row({"tenant_id": uuid.UUID(TEST_TENANT_ID), "id": uuid.uuid4()})
        update_row = mock_db_row(
            {"id": uuid.uuid4(), "role": "customer_admin", "active": False, "tenant_id": uuid.UUID(TEST_TENANT_ID)}
        )

        conn.fetchrow = AsyncMock(side_effect=[check_row, update_row])
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={"role": "customer_admin", "active": False},
            )

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_update_tenant_user_move_tenant_forbidden_for_non_super_admin(
        self, admin_client, override_current_user, fake_user_factory, mock_db_row, setup_silent_db_mock
    ):
        mod = _import_user_invitations_module()
        user = fake_user_factory("customer_admin")  # not super_admin
        conn = setup_silent_db_mock

        check_row = mock_db_row({"tenant_id": uuid.UUID(TEST_TENANT_ID), "id": uuid.uuid4()})
        conn.fetchrow = AsyncMock(return_value=check_row)
        conn.close = AsyncMock()

        with override_current_user(mod, user):
            response = admin_client.put(
                f"/api/user-invitations/users/{uuid.uuid4()}",
                json={"tenant_id": str(uuid.uuid4())},
            )

        assert response.status_code == 403
