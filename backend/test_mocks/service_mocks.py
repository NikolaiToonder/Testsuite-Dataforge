import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def setup_silent_db_mock(mocker):
    """
    Ensures no test ever hits the real database, 
    covering both pool-based and direct-connect patterns.
    """
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    
    # 1. Handle the "async with pool.acquire()" pattern (Existing)
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()

    # 2. Patch the custom lib getter (Existing)
    mocker.patch("app.libs.tenant_database.get_connection_pool", 
                 new_callable=AsyncMock, 
                 return_value=mock_pool)
    
    # 3. ADD THIS: Patch direct asyncpg connections (New for dashboard-layout)
    # This intercepts: conn = await asyncpg.connect(url)
    mocker.patch("asyncpg.connect", return_value=mock_conn)
    
    yield mock_conn


@pytest.fixture
def mock_db_row():
    """Returns a factory function to create mock DB rows that support dictionary access"""
    def _create_row(data_dict):
        row = MagicMock()
        # Allows row['column_name'] to work
        row.__getitem__.side_effect = data_dict.get
        return row
    return _create_row