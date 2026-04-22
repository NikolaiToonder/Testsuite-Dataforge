import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

@pytest.fixture
def mock_conn(mocker):
    """Fixture to mock the asyncpg connection"""
    mock_conn = AsyncMock()
    mocker.patch("asyncpg.connect", return_value=mock_conn)
    return mock_conn

class TestGetDataLogs:
    def test_get_data_logs_sensor_transformation(self, admin_client, mock_conn):
        """Test if sensor data is correctly transformed (hex conversion, etc)"""
        # Mocking a sensor row with bytes payload
        mock_row = {
            "id": "1",
            "timestamp": datetime.now(),
            "source": "Sensor A (EUI123)",
            "sensor_eui": "EUI123",
            "sensor_type": "temp",
            "raw_payload": b'\x01\x02\x03', # Testing the .hex() logic
            "rssi": -50,
            "snr": 7,
            "temp_c": 22.5,
            "humidity_rel_percent": None, # Should be filtered out of processed_data
            "co2_ppm": None,
            "illuminance_lux": None,
            "power_kw": None,
            "current_a": None,
            "voltage_v": None,
            "distance_mm": None,
            "part_detected": None,
            "qty_increment": None,
            "battery_level": 90,
            "signal_strength": 4,
            "target_table": "sensor_data",
            "status": "success"
        }
        
        # First call is for sensors, second (empty) for ERP
        mock_conn.fetch = AsyncMock(side_effect=[[mock_row], []])
        
        response = admin_client.get("/api/data-logs?data_type=sensor")
        
        assert response.status_code == 200
        data = response.json()
        
        entry = data["entries"][0]
        # Verify hex conversion worked
        assert entry["raw_data"]["raw_payload"] == "010203"
        # Verify None values were filtered out of processed_data
        assert "temp_c" in entry["processed_data"]
        assert "humidity_rel_percent" not in entry["processed_data"]


class TestGetDataStats:
    def test_get_data_statistics_success(self, admin_client, mock_conn):
        """Test the statistics aggregation endpoint"""
        # Mock the aggregate sensor stats
        mock_conn.fetchrow = AsyncMock(side_effect=[
            {"total_sensor_readings": 100, "active_sensors": 5, "readings_last_hour": 10, 
             "avg_signal_strength": 3.5, "parts_detected": 50},
            {"total_erp_configs": 2, "active_erp_configs": 1, "recent_syncs": 1}
        ])
        
        # Mock hourly activity
        mock_conn.fetch = AsyncMock(return_value=[
            {"hour": datetime.now(), "sensor_readings": 10}
        ])
        
        response = admin_client.get("/api/data-stats?hours_back=24")
        
        assert response.status_code == 200
        data = response.json()
        assert data["sensor_data"]["total_readings"] == 100
        assert data["erp_data"]["active_configurations"] == 1