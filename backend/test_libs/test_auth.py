import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException

from app.libs.tenant_models import UserRole, UserTenantInfo
from app.libs.auth import (
    AuthorizedUser,
    get_current_user_from_token,
    get_current_user,
    ensure_tenant_access,
    get_user_tenant_id,
    get_require_customer_user,
    get_require_customer_admin,
    get_require_super_admin,
)


def run(coro):
    """Helper to run async coroutines in sync tests."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------

def make_tenant_info(**kwargs) -> MagicMock:
    info = MagicMock(spec=UserTenantInfo)
    info.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
    info.user_role = kwargs.get("user_role", UserRole.CUSTOMER_USER)
    return info


def make_authorized_user(**kwargs) -> AuthorizedUser:
    return AuthorizedUser(
        sub=kwargs.get("sub", "user-001"),
        tenant_info=kwargs.get("tenant_info", make_tenant_info()),
        is_super_admin=kwargs.get("is_super_admin", False),
        acting_as_tenant_id=kwargs.get("acting_as_tenant_id", None),
    )


# ---------------------------------------------------------------------------
# AuthorizedUser
# ---------------------------------------------------------------------------

class TestAuthorizedUser:

    def test_tenant_id(self):
        tid = uuid.uuid4()
        user = make_authorized_user(tenant_info=make_tenant_info(tenant_id=tid))
        assert user.tenant_id == str(tid)

    def test_acting_as_tenant_takes_priority(self):
        acting_id = str(uuid.uuid4())
        user = make_authorized_user(acting_as_tenant_id=acting_id)
        assert user.tenant_id == acting_id

    def test_super_admin_has_all_roles(self):
        user = make_authorized_user(is_super_admin=True, tenant_info=None)
        for role in [UserRole.TENANT_READONLY, UserRole.CUSTOMER_USER, UserRole.CUSTOMER_ADMIN]:
            assert user.has_role(role) is True

    def test_role_hierarchy(self):
        user = make_authorized_user(tenant_info=make_tenant_info(user_role=UserRole.CUSTOMER_USER))
        assert user.has_role(UserRole.CUSTOMER_USER) is True
        assert user.has_role(UserRole.CUSTOMER_ADMIN) is False

    def test_admin_satisfies_lower_role(self):
        user = make_authorized_user(tenant_info=make_tenant_info(user_role=UserRole.CUSTOMER_ADMIN))
        assert user.has_role(UserRole.CUSTOMER_USER) is True

    def test_tenant_access(self):
        tid = uuid.uuid4()
        user = make_authorized_user(tenant_info=make_tenant_info(tenant_id=tid))
        assert user.can_access_tenant(str(tid)) is True
        assert user.can_access_tenant(str(uuid.uuid4())) is False

    def test_super_admin_tenant_access(self):
        user = make_authorized_user(is_super_admin=True)
        assert user.can_access_tenant(str(uuid.uuid4())) is True


# ---------------------------------------------------------------------------
# get_current_user_from_token
# ---------------------------------------------------------------------------

class TestGetCurrentUserFromToken:

    def test_missing_secret_key(self, mocker):
        mocker.patch("app.libs.auth.os.environ.get", return_value=None)
        mock_decode = mocker.patch("app.libs.auth.jwt.decode")

        with pytest.raises(HTTPException) as exc_info:
            run(get_current_user_from_token("Bearer sometoken"))

        assert exc_info.value.status_code == 401
        mock_decode.assert_not_called()

    def test_valid_token(self, mocker):
        tenant_info = make_tenant_info()
        mocker.patch("app.libs.auth.os.environ.get", return_value="some-secret")
        mocker.patch("app.libs.auth.jwt.decode", return_value={"sub": "user-123"})
        mocker.patch("app.libs.auth.get_user_tenant_info", new_callable=AsyncMock, return_value=tenant_info)
        mocker.patch("app.libs.auth.is_super_admin", new_callable=AsyncMock, return_value=False)

        result = run(get_current_user_from_token("Bearer validtoken"))

        assert result.sub == "user-123"
        assert result.tenant_info == tenant_info
        assert result.is_super_admin is False

    def test_invalid_token(self, mocker):
        from jose import JWTError
        mocker.patch("app.libs.auth.os.environ.get", return_value="some-secret")
        mocker.patch("app.libs.auth.jwt.decode", side_effect=JWTError("bad token"))

        with pytest.raises(HTTPException) as exc_info:
            run(get_current_user_from_token("Bearer badtoken"))

        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# get_current_user (acting-as-tenant header)
# ---------------------------------------------------------------------------

class TestGetCurrentUser:

    def test_super_admin_acting_as_tenant(self, mocker):
        tenant_id = str(uuid.uuid4())
        user = make_authorized_user(is_super_admin=True)
        mocker.patch("app.libs.auth.get_current_user_from_token", new_callable=AsyncMock, return_value=user)
        mocker.patch("app.libs.auth.get_tenant_by_id", new_callable=AsyncMock, return_value=MagicMock())

        result = run(get_current_user(authorization="Bearer token", x_acting_as_tenant=tenant_id))

        assert result.acting_as_tenant_id == tenant_id

    def test_non_super_admin_acting_as_tenant_ignored(self, mocker):
        user = make_authorized_user(is_super_admin=False)
        mocker.patch("app.libs.auth.get_current_user_from_token", new_callable=AsyncMock, return_value=user)
        mock_get_tenant = mocker.patch("app.libs.auth.get_tenant_by_id", new_callable=AsyncMock)

        result = run(get_current_user(authorization="Bearer token", x_acting_as_tenant=str(uuid.uuid4())))

        mock_get_tenant.assert_not_called()
        assert result.acting_as_tenant_id is None


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

class TestEnsureTenantAccess:

    def test_wrong_tenant_raises_403(self):
        user = make_authorized_user(tenant_info=make_tenant_info(tenant_id=uuid.uuid4()))
        with pytest.raises(HTTPException) as exc_info:
            ensure_tenant_access(user, str(uuid.uuid4()))
        assert exc_info.value.status_code == 403

    def test_super_admin_bypasses(self):
        user = make_authorized_user(is_super_admin=True, tenant_info=None)
        ensure_tenant_access(user, str(uuid.uuid4()))  # should not raise


class TestGetUserTenantId:

    def test_returns_id(self):
        tid = uuid.uuid4()
        user = make_authorized_user(tenant_info=make_tenant_info(tenant_id=tid))
        assert get_user_tenant_id(user) == str(tid)

    def test_no_tenant_raises_400(self):
        user = make_authorized_user(tenant_info=None)
        with pytest.raises(HTTPException) as exc_info:
            get_user_tenant_id(user)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------

class TestRoleGuards:

    def test_customer_user_passes(self):
        user = make_authorized_user(tenant_info=make_tenant_info(user_role=UserRole.CUSTOMER_USER))
        assert run(get_require_customer_user()(user)) is user

    def test_readonly_blocked(self):
        user = make_authorized_user(tenant_info=make_tenant_info(user_role=UserRole.TENANT_READONLY))
        with pytest.raises(HTTPException) as exc_info:
            run(get_require_customer_user()(user))
        assert exc_info.value.status_code == 403

    def test_customer_user_blocked_from_admin_route(self):
        user = make_authorized_user(tenant_info=make_tenant_info(user_role=UserRole.CUSTOMER_USER))
        with pytest.raises(HTTPException) as exc_info:
            run(get_require_customer_admin()(user))
        assert exc_info.value.status_code == 403

    def test_non_super_admin_blocked(self):
        user = make_authorized_user(is_super_admin=False)
        with pytest.raises(HTTPException) as exc_info:
            run(get_require_super_admin()(user))
        assert exc_info.value.status_code == 403

    def test_super_admin_passes_all(self):
        user = make_authorized_user(is_super_admin=True, tenant_info=None)
        for factory in [get_require_customer_user, get_require_customer_admin, get_require_super_admin]:
            assert run(factory()(user)) is user