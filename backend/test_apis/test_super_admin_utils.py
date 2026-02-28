import importlib
from unittest.mock import AsyncMock
import pytest

IMPORT_PATH = "app.libs.super_admin_utils"


@pytest.fixture
def super_admin_mod():
    return importlib.import_module(IMPORT_PATH)


def make_conn(fetchvals=None, *, fail_fetch=False, fail_close=False):
    conn = AsyncMock()
    conn._fetchvals = list(fetchvals or [])

    async def _fetchval_side_effect(*args, **kwargs):
        if fail_fetch:
            raise RuntimeError("fetchval failed")
        if not conn._fetchvals:
            return None
        return conn._fetchvals.pop(0)

    async def _close_side_effect():
        if fail_close:
            raise RuntimeError("close failed")
        return None

    conn.fetchval = AsyncMock(side_effect=_fetchval_side_effect)
    conn.close = AsyncMock(side_effect=_close_side_effect)
    return conn


class TestEnsureInnoveriaSuperAdmin:
    @pytest.mark.asyncio
    async def test_returns_true_if_already_super_admin(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fetchvals=[123])
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-1")

        assert res is True
        assert conn.fetchval.call_count == 1
        assert conn.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_if_no_email_found(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fetchvals=[None, None])
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-2")

        assert res is False
        assert conn.fetchval.call_count == 2
        assert conn.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_if_wrong_domain(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fetchvals=[None, "a@other.no"])
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-3")

        assert res is False
        assert conn.fetchval.call_count == 2
        assert conn.close.called is True

    @pytest.mark.asyncio
    async def test_inserts_and_returns_true_on_happy_path(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fetchvals=[None, "bob@innoveria.no", 999])
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-4")

        assert res is True
        assert conn.fetchval.call_count == 3
        assert conn.close.called is True

        insert_call = conn.fetchval.call_args_list[2]
        assert "INSERT INTO super_admins" in insert_call.args[0]

    @pytest.mark.asyncio
    async def test_provided_user_email_skips_db_email_lookup(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fetchvals=[None, 321])
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-5", user_email="x@innoveria.no")

        assert res is True
        assert conn.fetchval.call_count == 2
        assert conn.close.called is True

        queries = [c.args[0] for c in conn.fetchval.call_args_list]
        assert all("neon_auth.users_sync" not in q for q in queries)

    @pytest.mark.asyncio
    async def test_returns_false_if_connect_raises(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=RuntimeError("connect failed"))

        res = await super_admin_mod.ensure_innoveria_super_admin("user-6")
        assert res is False

    @pytest.mark.asyncio
    async def test_returns_false_if_fetchval_raises_and_attempts_close(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fail_fetch=True)
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-7")

        assert res is False
        assert conn.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_if_close_raises_in_except(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn = make_conn(fail_fetch=True, fail_close=True)
        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", return_value=conn)

        res = await super_admin_mod.ensure_innoveria_super_admin("user-8")

        assert res is False
        assert conn.close.called is True


class TestIsSuperAdminWithAutoRegister:
    @pytest.mark.asyncio
    async def test_returns_true_when_exists_true(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn1 = make_conn(fetchvals=[123])   # ensure early return
        conn2 = make_conn(fetchvals=[True])  # EXISTS True

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=[conn1, conn2])

        res = await super_admin_mod.is_super_admin_with_auto_register("user-9")

        assert res is True
        assert conn1.close.called is True
        assert conn2.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_when_exists_false(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn1 = make_conn(fetchvals=[None, None])  # ensure returns False
        conn2 = make_conn(fetchvals=[False])       # EXISTS False

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=[conn1, conn2])

        res = await super_admin_mod.is_super_admin_with_auto_register("user-10")
        assert res is False
        assert conn1.close.called is True
        assert conn2.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_when_exists_returns_none(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn1 = make_conn(fetchvals=[123])
        conn2 = make_conn(fetchvals=[None])

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=[conn1, conn2])

        res = await super_admin_mod.is_super_admin_with_auto_register("user-11")
        assert res is False
        assert conn1.close.called is True
        assert conn2.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_if_connect_raises(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=RuntimeError("connect failed"))

        res = await super_admin_mod.is_super_admin_with_auto_register("user-12")
        assert res is False

    @pytest.mark.asyncio
    async def test_returns_false_if_exists_fetchval_raises_and_attempts_close(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn1 = make_conn(fetchvals=[123])
        conn2 = make_conn(fetchvals=[], fail_fetch=True)

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=[conn1, conn2])

        res = await super_admin_mod.is_super_admin_with_auto_register("user-13")
        assert res is False
        assert conn1.close.called is True
        assert conn2.close.called is True

    @pytest.mark.asyncio
    async def test_returns_false_if_close_raises_in_except(self, mocker, monkeypatch, super_admin_mod):
        monkeypatch.setenv("DATABASE_URL", "postgresql://x")

        conn1 = make_conn(fetchvals=[123])
        conn2 = make_conn(fetchvals=[], fail_fetch=True, fail_close=True)

        mocker.patch(f"{IMPORT_PATH}.asyncpg.connect", side_effect=[conn1, conn2])

        res = await super_admin_mod.is_super_admin_with_auto_register("user-14")
        assert res is False
        assert conn1.close.called is True
        assert conn2.close.called is True