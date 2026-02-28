import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json
import sys

@pytest.fixture(autouse=True)
def mock_db_connection(mocker):
    """Auto-mock database connection for all device tests"""
    mock_conn = AsyncMock()
    mock_conn.close = AsyncMock()
    
    # Mock transaction context manager
    mock_transaction = MagicMock()
    mock_transaction.__aenter__ = AsyncMock(return_value=mock_transaction)
    mock_transaction.__aexit__ = AsyncMock(return_value=None)
    mock_conn.transaction = MagicMock(return_value=mock_transaction)
    
    mocker.patch("app.libs.database.get_db_connection", return_value=mock_conn)
    return mock_conn


class TestListGateways:
    """Test suite for GET /devices/gateways endpoint"""

    def test_list_gateways_regular_user(self, admin_client, mocker, mock_db_row, mock_db_connection, mock_tenant_info):
        """Test listing gateways as regular user"""
        mocker.patch("app.libs.tenant_database.is_super_admin", new_callable=AsyncMock, return_value=False)
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        mock_gateways = [
            mock_db_row({
                "id": "gateway-1",
                "tenant_id": "tenant-1",
                "name": "Gateway A",
                "description": "Main gateway",
                "gateway_eui": "1234567890ABCDEF",
                "location": "Building 1",
                "latitude": 59.9139,
                "longitude": 10.7522,
                "status": "active",
                "last_seen_at": datetime(2024, 1, 1),
                "firmware_version": "1.0.0",
                "hardware_version": "1.0",
                "network_config": json.dumps({"key": "value"}),
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1),
                "department_id": "dept-1",
                "department_name": "Production"
            })
        ]
        
        mock_db_connection.fetch = AsyncMock(return_value=mock_gateways)
        
        response = admin_client.get("/api/devices/gateways")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Gateway A"

    def test_list_gateways_super_admin(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test listing gateways as super admin (all tenants)"""
        mocker.patch("app.libs.tenant_database.is_super_admin", new_callable=AsyncMock, return_value=True)
        
        mock_gateways = [
            mock_db_row({
                "id": "gateway-1",
                "tenant_id": "tenant-1",
                "name": "Gateway A",
                "description": None,
                "gateway_eui": "1234567890ABCDEF",
                "location": None,
                "latitude": None,
                "longitude": None,
                "status": "active",
                "last_seen_at": None,
                "firmware_version": None,
                "hardware_version": None,
                "network_config": "{}",
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1),
                "department_id": None,
                "department_name": None,
                "tenant_name": "Tenant A"
            })
        ]
        
        mock_db_connection.fetch = AsyncMock(return_value=mock_gateways)
        
        response = admin_client.get("/api/devices/gateways")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_gateways_no_tenant(self, admin_client, mocker, mock_db_connection):
        """Test listing gateways when user has no tenant"""
        mocker.patch("app.libs.tenant_database.is_super_admin", new_callable=AsyncMock, return_value=False)
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        response = admin_client.get("/api/devices/gateways")
        
        assert response.status_code == 403


class TestCreateGateway:
    """Test suite for POST /devices/gateways endpoint"""

    def test_create_gateway_success(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test creating a new gateway"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        gateway_data = {
            "name": "New Gateway",
            "description": "Gateway description",
            "gateway_eui": "AABBCCDDEEFF0011",
            "department_id": "dept-1",
            "latitude": 59.9139,
            "longitude": 10.7522,
            "network_config": {"frequency": "868MHz"}
        }
        
        created_row = mock_db_row({
            "id": "gateway-new",
            "tenant_id": "tenant-1",
            "name": "New Gateway",
            "description": "Gateway description",
            "gateway_eui": "AABBCCDDEEFF0011",
            "location": None,
            "latitude": 59.9139,
            "longitude": 10.7522,
            "status": "inactive",
            "last_seen_at": None,
            "firmware_version": None,
            "hardware_version": None,
            "network_config": json.dumps({"frequency": "868MHz"}),
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1),
            "department_id": "dept-1",
            "department_name": "Production"
        })
        
        # fetchrow calls: check existing, insert, get with department
        mock_db_connection.fetchrow = AsyncMock(side_effect=[None, created_row, created_row])
        
        response = admin_client.post("/api/devices/gateways", json=gateway_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Gateway"
        assert data["gateway_eui"] == "AABBCCDDEEFF0011"

    def test_create_gateway_duplicate_eui(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test creating gateway with duplicate EUI"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        gateway_data = {
            "name": "New Gateway",
            "gateway_eui": "EXISTING_EUI"
        }
        
        existing_row = mock_db_row({"id": "gateway-existing"})
        mock_db_connection.fetchrow = AsyncMock(return_value=existing_row)
        
        response = admin_client.post("/api/devices/gateways", json=gateway_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpdateGateway:
    """Test suite for PUT /devices/gateways/{gateway_id} endpoint"""

    def test_update_gateway_success(self, admin_client, mocker, mock_db_row, mock_db_connection, mock_tenant_info):
        """Test updating gateway"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        update_data = {
            "name": "Updated Gateway",
            "description": "Updated description"
        }
        
        updated_row = mock_db_row({
            "id": "gateway-1",
            "tenant_id": "tenant-1",
            "name": "Updated Gateway",
            "description": "Updated description",
            "gateway_eui": "1234567890ABCDEF",
            "location": None,
            "latitude": None,
            "longitude": None,
            "status": "active",
            "last_seen_at": None,
            "firmware_version": None,
            "hardware_version": None,
            "network_config": "{}",
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 2),
            "department_id": None,
            "department_name": None
        })
        
        # fetchrow calls: update, get with department
        mock_db_connection.fetchrow = AsyncMock(side_effect=[updated_row, updated_row])
        
        response = admin_client.put("/api/devices/gateways/gateway-1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Gateway"

    def test_update_gateway_not_found(self, admin_client, mocker, mock_db_connection, mock_tenant_info):
        """Test updating non-existent gateway"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        update_data = {"name": "Updated"}
        
        mock_db_connection.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.put("/api/devices/gateways/nonexistent", json=update_data)
        
        assert response.status_code == 404


class TestDeleteGateway:
    """Test suite for DELETE /devices/gateways/{gateway_id} endpoint"""

    def test_delete_gateway_success(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test deleting gateway"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        gateway_row = mock_db_row({"id": "gateway-1"})
        
        mock_db_connection.fetchrow = AsyncMock(return_value=gateway_row)
        mock_db_connection.execute = AsyncMock()
        
        response = admin_client.delete("/api/devices/gateways/11111111-1111-1111-1111-111111111111")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_delete_gateway_not_found(self, admin_client, mocker, mock_db_connection):
        """Test deleting non-existent gateway"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        mock_db_connection.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.delete("/api/devices/gateways/11111111-1111-1111-1111-111111111111")
        
        assert response.status_code == 404

    def test_delete_gateway_invalid_uuid(self, admin_client, mocker):
        """Test deleting gateway with invalid UUID"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        response = admin_client.delete("/api/devices/gateways/invalid-uuid")
        
        assert response.status_code == 400


class TestListSensors:
    """Test suite for GET /devices/sensors endpoint"""

    def test_list_sensors_regular_tenant(self, admin_client, mocker, mock_db_row):
        """Test listing sensors for regular tenant"""
        # Mock connection pool
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_acquire = MagicMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire)
        
        mocker.patch("app.libs.database.get_connection_pool", new_callable=AsyncMock, return_value=mock_pool)
        
        mock_sensors = [
            mock_db_row({
                "id": "sensor-1",
                "tenant_id": "tenant-1",
                "name": "Temperature Sensor",
                "description": "Main temp sensor",
                "sensor_type": "temperature",
                "sensor_eui": "AABBCCDDEEFF0011",
                "gateway_id": "gateway-1",
                "machine_id": None,
                "location": "Zone A",
                "latitude": None,
                "longitude": None,
                "status": "active",
                "last_seen": None,
                "data_category": "environmental",
                "voltage_type": "3.3V",
                "model": None,
                "firmware_version": None,
                "hardware_version": None,
                "sampling_rate_seconds": 60,
                "min_value": None,
                "max_value": None,
                "precision_digits": 2,
                "unit": "°C",
                "scale_factor": None,
                "offset_value": None,
                "config": "{}",
                "active": True,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1)
            })
        ]
        
        # fetchval for tenant type, fetch for sensors
        mock_conn.fetchval = AsyncMock(return_value="factory")
        mock_conn.fetch = AsyncMock(return_value=mock_sensors)
        
        response = admin_client.get("/api/devices/sensors")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Temperature Sensor"

    def test_list_sensors_industrial_park(self, admin_client, mocker, mock_db_row):
        """Test listing sensors for industrial park (aggregates children)"""
        # Mock connection pool
        mock_conn = AsyncMock()
        mock_pool = MagicMock()
        mock_acquire = MagicMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock()
        mock_pool.acquire = MagicMock(return_value=mock_acquire)
        
        mocker.patch("app.libs.database.get_connection_pool", new_callable=AsyncMock, return_value=mock_pool)
        
        mock_sensors = [
            mock_db_row({
                "id": "sensor-1",
                "tenant_id": "tenant-1",
                "name": "Sensor 1",
                "description": None,
                "sensor_type": "temperature",
                "sensor_eui": "AABB",
                "gateway_id": None,
                "machine_id": None,
                "location": None,
                "latitude": None,
                "longitude": None,
                "status": "active",
                "last_seen": None,
                "data_category": None,
                "voltage_type": None,
                "model": None,
                "firmware_version": None,
                "hardware_version": None,
                "sampling_rate_seconds": None,
                "min_value": None,
                "max_value": None,
                "precision_digits": None,
                "unit": None,
                "scale_factor": None,
                "offset_value": None,
                "config": "{}",
                "active": True,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1),
                "tenant_name": "Factory A"
            })
        ]
        
        mock_conn.fetchval = AsyncMock(return_value="industrial_park")
        mock_conn.fetch = AsyncMock(return_value=mock_sensors)
        
        response = admin_client.get("/api/devices/sensors")
        
        assert response.status_code == 200


class TestCreateSensor:
    """Test suite for POST /devices/sensors endpoint"""

    def test_create_sensor_success(self, admin_client, mocker, mock_db_row, mock_db_connection, mock_tenant_info):
        """Test creating a new sensor"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        sensor_data = {
            "name": "New Sensor",
            "description": "Test sensor",
            "sensor_type": "temperature",
            "sensor_eui": "AABBCCDDEEFF0011",
            "gateway_id": "11111111-1111-1111-1111-111111111111",
            "location": "Zone A",
            "data_category": "environmental",
            "voltage_type": "3.3V",
            "unit": "°C",
            "sampling_rate_seconds": 60
        }
        
        created_row = mock_db_row({
            "id": "sensor-new",
            "created_at": datetime(2024, 1, 1)
        })
        
        gateway_row = mock_db_row({"id": "gateway-1"})
        
        # fetchrow calls: check existing sensor, validate gateway, insert sensor
        mock_db_connection.fetchrow = AsyncMock(side_effect=[None, gateway_row, created_row])
        
        response = admin_client.post("/api/devices/sensors", json=sensor_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Sensor created successfully"
        assert data["sensor"]["name"] == "New Sensor"

    def test_create_sensor_duplicate_eui(self, admin_client, mocker, mock_db_row, mock_db_connection, mock_tenant_info):
        """Test creating sensor with duplicate EUI"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        sensor_data = {
            "name": "New Sensor",
            "sensor_type": "temperature",
            "sensor_eui": "EXISTING_EUI"
        }
        
        existing_row = mock_db_row({"id": "sensor-existing"})
        mock_db_connection.fetchrow = AsyncMock(return_value=existing_row)
        
        response = admin_client.post("/api/devices/sensors", json=sensor_data)
        
        assert response.status_code == 400
        assert "eksisterer allerede" in response.json()["detail"]

    def test_create_sensor_gateway_not_found(self, admin_client, mocker, mock_db_connection, mock_tenant_info):
        """Test creating sensor with non-existent gateway"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        sensor_data = {
            "name": "New Sensor",
            "sensor_type": "temperature",
            "sensor_eui": "AABB",
            "gateway_id": "11111111-1111-1111-1111-111111111111"
        }
        
        # fetchrow calls: check existing sensor, validate gateway (returns None)
        mock_db_connection.fetchrow = AsyncMock(side_effect=[None, None])
        
        response = admin_client.post("/api/devices/sensors", json=sensor_data)
        
        assert response.status_code == 404
        assert "Gateway not found" in response.json()["detail"]

    def test_create_sensor_no_tenant(self, admin_client, mocker, mock_db_connection):
        """Test creating sensor when user has no tenant"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=None)
        
        sensor_data = {
            "name": "New Sensor",
            "sensor_type": "temperature",
            "sensor_eui": "AABB"
        }
        
        response = admin_client.post("/api/devices/sensors", json=sensor_data)
        
        assert response.status_code == 403


class TestGetSensor:
    """Test suite for GET /devices/sensors/{sensor_id} endpoint"""

    def test_get_sensor_success(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test getting sensor by ID"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        sensor_row = mock_db_row({
            "id": "sensor-1",
            "tenant_id": "tenant-1",
            "name": "Temperature Sensor",
            "description": None,
            "sensor_type": "temperature",
            "sensor_eui": "AABB",
            "gateway_id": None,
            "machine_id": None,
            "location": None,
            "latitude": None,
            "longitude": None,
            "status": "active",
            "last_seen": None,
            "battery_level": None,
            "signal_strength": None,
            "data_category": None,
            "voltage_type": None,
            "model": None,
            "firmware_version": None,
            "hardware_version": None,
            "sampling_rate_seconds": None,
            "min_value": None,
            "max_value": None,
            "precision_digits": None,
            "unit": None,
            "scale_factor": None,
            "offset_value": None,
            "config": {},
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 1)
        })
        
        mock_db_connection.fetchrow = AsyncMock(return_value=sensor_row)
        
        response = admin_client.get("/api/devices/sensors/sensor-1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Temperature Sensor"

    def test_get_sensor_not_found(self, admin_client, mocker, mock_db_connection):
        """Test getting non-existent sensor"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        mock_db_connection.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.get("/api/devices/sensors/nonexistent")
        
        assert response.status_code == 404


class TestUpdateSensor:
    """Test suite for PUT /devices/sensors/{sensor_id} endpoint"""

    def test_update_sensor_success(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test updating sensor"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        update_data = {
            "name": "Updated Sensor",
            "location": "New Location"
        }
        
        existing_row = mock_db_row({
            "id": "sensor-1",
            "sensor_eui": "AABB"
        })
        
        updated_row = mock_db_row({
            "id": "sensor-1",
            "tenant_id": "tenant-1",
            "name": "Updated Sensor",
            "description": None,
            "sensor_eui": "AABB",
            "sensor_type": "temperature",
            "gateway_id": None,
            "machine_id": None,
            "location": "New Location",
            "latitude": None,
            "longitude": None,
            "status": "active",
            "last_seen_at": None,
            "battery_level": None,
            "signal_strength": None,
            "firmware_version": None,
            "hardware_version": None,
            "unit": None,
            "sampling_rate_seconds": None,
            "min_value": None,
            "max_value": None,
            "precision_digits": None,
            "scale_factor": None,
            "offset_value": None,
            "model": None,
            "config": "{}",
            "created_at": datetime(2024, 1, 1),
            "updated_at": datetime(2024, 1, 2)
        })
        
        # fetchrow calls: check exists, update
        mock_db_connection.fetchrow = AsyncMock(side_effect=[existing_row, updated_row])
        
        response = admin_client.put("/api/devices/sensors/sensor-1", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Sensor"
        assert data["location"] == "New Location"

    def test_update_sensor_not_found(self, admin_client, mocker, mock_db_connection):
        """Test updating non-existent sensor"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        update_data = {"name": "Updated"}
        
        mock_db_connection.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.put("/api/devices/sensors/nonexistent", json=update_data)
        
        assert response.status_code == 404

    def test_update_sensor_duplicate_eui(self, admin_client, mocker, mock_db_row, mock_db_connection):
        """Test updating sensor with duplicate EUI"""
        mocker.patch("app.libs.auth.get_user_tenant_id", return_value="tenant-1")
        
        update_data = {"sensor_eui": "DUPLICATE_EUI"}
        
        existing_row = mock_db_row({
            "id": "sensor-1",
            "sensor_eui": "ORIGINAL_EUI"
        })
        
        duplicate_row = mock_db_row({"id": "sensor-2"})
        
        # fetchrow calls: check exists, check EUI conflict
        mock_db_connection.fetchrow = AsyncMock(side_effect=[existing_row, duplicate_row])
        
        response = admin_client.put("/api/devices/sensors/sensor-1", json=update_data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestDeleteSensor:
    """Test suite for DELETE /devices/sensors/{sensor_id} endpoint"""

    def test_delete_sensor_success(self, admin_client, mocker, mock_db_row, mock_db_connection, mock_tenant_info):
        """Test soft deleting sensor"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        sensor_row = mock_db_row({"id": "sensor-1"})
        
        mock_db_connection.fetchrow = AsyncMock(return_value=sensor_row)
        mock_db_connection.execute = AsyncMock()
        
        response = admin_client.delete("/api/devices/sensors/11111111-1111-1111-1111-111111111111")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        # Verify soft delete was called (name appended with DELETED)
        assert mock_db_connection.execute.call_count == 2  # Update and delete machine_sensors

    def test_delete_sensor_not_found(self, admin_client, mocker, mock_db_connection, mock_tenant_info):
        """Test deleting non-existent sensor"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        mock_db_connection.fetchrow = AsyncMock(return_value=None)
        
        response = admin_client.delete("/api/devices/sensors/11111111-1111-1111-1111-111111111111")
        
        assert response.status_code == 404

    def test_delete_sensor_invalid_uuid(self, admin_client, mocker):
        """Test deleting sensor with invalid UUID"""
        response = admin_client.delete("/api/devices/sensors/invalid-uuid")
        
        assert response.status_code == 400


class TestSensorHealthStatus:
    """Test suite for GET /devices/sensors/health-status endpoint"""

    def test_get_sensors_health_status(self, admin_client, mocker, mock_db_row, mock_db_connection, mock_tenant_info):
        """Test getting sensor health status overview"""
        mocker.patch("app.libs.tenant_utils.get_user_tenant_info", new_callable=AsyncMock, return_value=mock_tenant_info)
        
        health_row = mock_db_row({
            "total_sensors": 10,
            "active_sensors": 8,
            "inactive_sensors": 2,
            "online_sensors": 6,
            "low_battery_sensors": 3,
            "poor_signal_sensors": 1
        })
        
        mock_db_connection.fetchrow = AsyncMock(return_value=health_row)
        
        response = admin_client.get("/api/devices/sensors/health-status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_sensors"] == 10
        assert data["active_sensors"] == 8
        assert data["low_battery_sensors"] == 3


class TestListSensorTypes:
    """Test suite for GET /devices/sensor-types endpoint"""

    def test_list_sensor_types(self, admin_client, mock_db_row, mock_db_connection):
        """Test listing sensor type configurations"""
        mock_types = [
            mock_db_row({
                "id": "type-1",
                "name": "temperature",
                "description": "Temperature sensor",
                "standard_fields": json.dumps(["value"]),
                "unit_mappings": json.dumps({"celsius": "°C"}),
                "validation_rules": json.dumps({"min": -50, "max": 150}),
                "default_config": json.dumps({"sampling_rate": 60}),
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1)
            })
        ]
        
        mock_db_connection.fetch = AsyncMock(return_value=mock_types)
        
        response = admin_client.get("/api/devices/sensor-types")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "temperature"


class TestDevicesAuthorization:
    """Test suite for device authorization"""

    def test_unauthenticated_access_denied(self, unauthenticated_client):
        """Test that unauthenticated requests are rejected"""
        response = unauthenticated_client.get("/api/devices/gateways")
        assert response.status_code == 401
        
        response = unauthenticated_client.get("/api/devices/sensors")
        assert response.status_code == 401