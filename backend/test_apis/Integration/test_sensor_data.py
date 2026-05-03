import uuid
from datetime import datetime, timezone

import pytest

TEST_TENANT_ID = "11111111-1111-1111-1111-111111111111"

READINGS_URL = "/api/readings"


# --- Mock factories ---

def _tenant_row():
    return {"tenant_id": uuid.UUID(TEST_TENANT_ID)}


def _reading_row(**overrides):
    base = {
        "sensor_id": "1",
        "sensor_eui": "EUI1",
        "sensor_name": "Sensor 1",
        "timestamp": datetime.now(timezone.utc),
        "temp_c": 20.0,
        "humidity_rel_percent": None,
        "co2_ppm": None,
        "illuminance_lux": None,
        "power_kw": None,
        "current_a": None,
        "voltage_v": None,
        "battery_level": None,
        "signal_strength": None,
        "rssi": None,
        "snr": None,
        "distance_mm": None,
        "part_detected": None,
        "qty_increment": None,
        "vibration_rms_g": None,
        "vibration_hz": None,
        "weight_kg": None,
    }
    base.update(overrides)
    return base


# --- Tests ---

class TestReadingsSuccess:
    """Basic success cases for GET /api/readings"""

    def test_returns_200_with_readings(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = [mock_db_row(_reading_row())]

        r = client.get(f"{READINGS_URL}?hours_back=24")

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True
        assert body["total_count"] == 1
        assert body["readings"][0]["sensor_eui"] == "EUI1"

    def test_null_part_detected_defaults_to_false(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = [mock_db_row(_reading_row(part_detected=None))]

        r = client.get(f"{READINGS_URL}?hours_back=24")

        assert r.status_code == 200, r.text
        assert r.json()["readings"][0]["part_detected"] is False

    def test_null_qty_increment_defaults_to_zero(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = [mock_db_row(_reading_row(qty_increment=None))]

        r = client.get(f"{READINGS_URL}?hours_back=24")

        assert r.status_code == 200, r.text
        assert r.json()["readings"][0]["qty_increment"] == 0

    def test_db_connection_is_closed(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = [mock_db_row(_reading_row())]

        client.get(f"{READINGS_URL}?hours_back=24")

        assert mock_conn.close.await_count >= 1

    def test_empty_result(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = []

        r = client.get(f"{READINGS_URL}?hours_back=24")

        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_count"] == 0
        assert body["readings"] == []


class TestReadingsFilters:
    """Query filter behaviour for GET /api/readings"""

    def test_filter_by_sensor_euis(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = []

        r = client.get(f"{READINGS_URL}?sensor_euis=E1,E2&hours_back=5")

        assert r.status_code == 200, r.text
        args, _ = mock_conn.fetch.call_args
        query, *params = args
        assert "s.sensor_eui = ANY($4)" in query
        assert params[3] == ["E1", "E2"]

    def test_filter_by_machine_ids(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = []

        r = client.get(f"{READINGS_URL}?machine_ids=M1,M2&hours_back=5")

        assert r.status_code == 200, r.text
        args, _ = mock_conn.fetch.call_args
        query, *params = args
        assert "s.sensor_eui = ANY($4)" in query
        assert params[3] == ["M1", "M2"]

    def test_filter_by_both_sensor_euis_and_machine_ids(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.return_value = []

        r = client.get(f"{READINGS_URL}?sensor_euis=E1,E2&machine_ids=M1,M2&hours_back=5")

        assert r.status_code == 200, r.text
        args, _ = mock_conn.fetch.call_args
        query, *params = args
        assert "s.sensor_eui = ANY($4)" in query
        assert "s.sensor_eui = ANY($5)" in query
        assert params[3] == ["E1", "E2"]
        assert params[4] == ["M1", "M2"]


class TestReadingsValidation:
    """Input validation for GET /api/readings"""

    def test_hours_back_too_large_returns_422(self, client):
        r = client.get(f"{READINGS_URL}?hours_back=999")
        assert r.status_code == 422

    def test_missing_hours_back_returns_422(self, client):
        r = client.get(READINGS_URL)
        assert r.status_code == 422


class TestReadingsErrors:
    """Error handling for GET /api/readings"""

    def test_db_failure_returns_500(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.side_effect = RuntimeError("db down")

        r = client.get(f"{READINGS_URL}?hours_back=24")

        assert r.status_code == 500
        assert "Failed to retrieve sensor readings" in r.json()["detail"]

    def test_db_connection_closed_on_failure(self, client, setup_silent_db_mock, mock_db_row):
        mock_conn = setup_silent_db_mock
        mock_conn.fetchrow.return_value = mock_db_row(_tenant_row())
        mock_conn.fetch.side_effect = RuntimeError("db down")

        client.get(f"{READINGS_URL}?hours_back=24")

        assert mock_conn.close.await_count >= 1