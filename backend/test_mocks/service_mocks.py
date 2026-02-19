import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def setup_silent_db_mock(mocker):
    """
    Ensures no test ever hits the real database,
    covering both pool-based and direct-connect patterns.
    """
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock()
    mocker.patch(
        "app.libs.tenant_database.get_connection_pool",
        new_callable=AsyncMock,
        return_value=mock_pool
    )
    mocker.patch("asyncpg.connect", return_value=mock_conn)
    yield mock_conn


@pytest.fixture
def mock_db_row():
    """
    Returns a factory function to create mock DB rows that support
    dictionary-style access (row['key']).

    Raises KeyError for missing keys — same behaviour as a real asyncpg
    Record — so tests fail loudly if the source code tries to access a
    key that was not set up in the mock.
    """
    def _create_row(data_dict: dict):
        row = MagicMock()

        # row['key'] — raises KeyError on missing keys
        row.__getitem__.side_effect = lambda key: data_dict[key]

        # 'key' in row
        row.__contains__.side_effect = lambda key: key in data_dict

        # row.get('key') / row.get('key', default)
        row.get.side_effect = data_dict.get

        return row

    return _create_row