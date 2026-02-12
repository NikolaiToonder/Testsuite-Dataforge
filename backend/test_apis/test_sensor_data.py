import uuid
from datetime import datetime, timezone
from test_mocks.auth_mocks import TEST_TENANT_ID

READINGS_URL = "/api/readings"

def _tenant_fetchrow_result():
    return {
        "tenant_id": uuid.UUID(TEST_TENANT_ID)
    }


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


def test_readings_success(client, global_db_blocker):
    mock_conn = global_db_blocker
    mock_conn.fetchrow.return_value = _tenant_fetchrow_result()
    mock_conn.fetch.return_value = [_reading_row()]

    r = client.get(f"{READINGS_URL}?hours_back=24")
    assert r.status_code == 200, r.text

    body = r.json()
    assert body["success"] is True
    assert body["total_count"] == 1
    assert body["readings"][0]["sensor_eui"] == "EUI1"
    assert body["readings"][0]["part_detected"] is False
    assert body["readings"][0]["qty_increment"] == 0

    assert mock_conn.close.await_count >= 1


def test_readings_sensor_euis(client, global_db_blocker):
    mock_conn = global_db_blocker
    mock_conn.fetchrow.return_value = _tenant_fetchrow_result()
    mock_conn.fetch.return_value = []

    r = client.get(f"{READINGS_URL}?sensor_euis=E1,E2&hours_back=5")
    assert r.status_code == 200, r.text

    args, _kwargs = mock_conn.fetch.call_args
    query = args[0]
    params = args[1:]

    assert "s.sensor_eui = ANY($4)" in query
    assert params[3] == ["E1", "E2"]


def test_readings_machine_ids(client, global_db_blocker):
    mock_conn = global_db_blocker
    mock_conn.fetchrow.return_value = _tenant_fetchrow_result()
    mock_conn.fetch.return_value = []

    r = client.get(f"{READINGS_URL}?machine_ids=M1,M2&hours_back=5")
    assert r.status_code == 200, r.text

    args, _kwargs = mock_conn.fetch.call_args
    query = args[0]
    params = args[1:]

    assert "s.sensor_eui = ANY($4)" in query
    assert params[3] == ["M1", "M2"]


def test_readings_filters(client, global_db_blocker):
    mock_conn = global_db_blocker
    mock_conn.fetchrow.return_value = _tenant_fetchrow_result()
    mock_conn.fetch.return_value = []

    r = client.get(f"{READINGS_URL}?sensor_euis=E1,E2&machine_ids=M1,M2&hours_back=5")
    assert r.status_code == 200, r.text

    args, _kwargs = mock_conn.fetch.call_args
    query = args[0]
    params = args[1:]

    assert "s.sensor_eui = ANY($4)" in query
    assert "s.sensor_eui = ANY($5)" in query
    assert params[3] == ["E1", "E2"]
    assert params[4] == ["M1", "M2"]


def test_readings_hours_back_validation(client):
    r = client.get(f"{READINGS_URL}?hours_back=999")
    assert r.status_code == 422


def test_readings_db_failure(client, global_db_blocker):
    mock_conn = global_db_blocker
    mock_conn.fetchrow.return_value = _tenant_fetchrow_result()
    mock_conn.fetch.side_effect = RuntimeError("db down")

    r = client.get(f"{READINGS_URL}?hours_back=24")
    assert r.status_code == 500

    body = r.json()
    assert "Failed to retrieve sensor readings" in body["detail"]
    assert mock_conn.close.await_count >= 1
