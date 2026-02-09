import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def setup_silent_db_mock():
    """
    Ensures no test ever hits the real database.
    Returns a generic mock connection.
    """
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    
    # Setup the "async with pool.acquire()" pattern
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()

    with patch("app.libs.tenant_database.get_connection_pool", new_callable=AsyncMock) as mocked_getter:
        mocked_getter.return_value = mock_pool
        yield mock_conn