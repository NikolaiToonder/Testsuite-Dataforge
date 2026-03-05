import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


TENANT_ID = "11111111-1111-1111-1111-111111111111"


def db_execute(db, query, *args):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(db.execute(query, *args))


def db_fetchrow(db, query, *args):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(db.fetchrow(query, *args))


def make_webhook_body(sensor_eui="AABBCCDDEEFF0011", hex_data="0102030405060708", rssi=-80, snr=7.5):
    return {
        "devEUI": sensor_eui,
        "data": hex_data,
        "time": "2024-01-01T12:00:00Z",
        "rxInfo": [{"rssi": rssi, "loRaSNR": snr}]
    }


def insert_sensor(db, sensor_eui, sensor_type="power_3phase", model="HotDrop"):
    sensor_id = str(uuid.uuid4())
    db_execute(db,
        """
        INSERT INTO sensors (id, tenant_id, sensor_eui, sensor_type, model, name)
        VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6)
        """,
        sensor_id, TENANT_ID, sensor_eui, sensor_type, model, f"Sensor {sensor_eui[:8]}"
    )
    return sensor_id


class TestWebhookEndpoint:

    def test_get_test_endpoint(self, admin_client):
        response = admin_client.get("/api/lorawan/test")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_missing_data_payload(self, admin_client):
        body = make_webhook_body(hex_data="")
        response = admin_client.post("/api/lorawan/webhook", json=body)
        assert response.status_code == 400

    def test_known_power_sensor_stores_data(self, admin_client, db, mocker):
        eui = "AABBCCDDEEFF0011"
        insert_sensor(db, eui, sensor_type="power_3phase", model="HotDrop")

        mocker.patch("app.apis.lorawan_webhook.websocket_manager.broadcast", new_callable=AsyncMock)
        mocker.patch("app.apis.lorawan_webhook.decode_sensor_payload", return_value={
            "sensor_type": "power_3phase",
            "rms_amps": 12.5,
            "power_kw": 5.0,
            "battery_level": 80
        })

        response = admin_client.post("/api/lorawan/webhook", json=make_webhook_body(sensor_eui=eui))

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["sensor_eui"] == eui
        assert data["rms_amps"] == 12.5

    def test_known_power_sensor_writes_to_db(self, admin_client, db, mocker):
        eui = "BBCCDDEEFF001122"
        insert_sensor(db, eui, sensor_type="power_3phase")

        mocker.patch("app.apis.lorawan_webhook.websocket_manager.broadcast", new_callable=AsyncMock)
        mocker.patch("app.apis.lorawan_webhook.decode_sensor_payload", return_value={
            "sensor_type": "power_3phase",
            "rms_amps": 8.0,
            "power_kw": 3.2,
            "battery_level": 90
        })

        admin_client.post("/api/lorawan/webhook", json=make_webhook_body(sensor_eui=eui))

        row = db_fetchrow(db, "SELECT * FROM sensor_data WHERE tenant_id = $1::uuid", TENANT_ID)
        assert row is not None
        assert float(row["current_a"]) == pytest.approx(8.0)
        assert float(row["power_kw"]) == pytest.approx(3.2)

    def test_unknown_sensor_returns_500(self, admin_client, db, mocker):
        mocker.patch("app.apis.lorawan_webhook.websocket_manager.broadcast", new_callable=AsyncMock)
        mocker.patch("app.apis.lorawan_webhook.decode_sensor_payload", return_value={
            "sensor_type": "power_3phase", "rms_amps": 1.0
        })

        response = admin_client.post("/api/lorawan/webhook",
                                     json=make_webhook_body(sensor_eui="UNKNOWNEUI00001"))
        assert response.status_code == 500

    def test_distance_sensor_stores_part_detection(self, admin_client, db, mocker):
        eui = "CCDDEEFF00112233"
        insert_sensor(db, eui, sensor_type="distance", model="SensingLabs")

        mocker.patch("app.apis.lorawan_webhook.websocket_manager.broadcast", new_callable=AsyncMock)
        mocker.patch("app.apis.lorawan_webhook.decode_sensor_payload", return_value={
            "sensor_type": "distance",
            "distance_mm": 150,
            "part_detected": True,
            "battery_level": 70
        })
        mocker.patch("app.apis.lorawan_webhook.calculate_part_detection", return_value=(True, 1))

        response = admin_client.post("/api/lorawan/webhook", json=make_webhook_body(sensor_eui=eui))

        assert response.status_code == 200
        data = response.json()
        assert data["part_detected"] is True
        assert data["distance_mm"] == 150

    def test_websocket_broadcast_called_on_success(self, admin_client, db, mocker):
        eui = "DDEEFF0011223344"
        insert_sensor(db, eui, sensor_type="power_1phase")

        mock_broadcast = mocker.patch(
            "app.apis.lorawan_webhook.websocket_manager.broadcast", new_callable=AsyncMock
        )
        mocker.patch("app.apis.lorawan_webhook.decode_sensor_payload", return_value={
            "sensor_type": "power_1phase",
            "rms_amps": 5.0,
            "power_kw": 1.1
        })

        admin_client.post("/api/lorawan/webhook", json=make_webhook_body(sensor_eui=eui))

        mock_broadcast.assert_called_once()
        broadcast_payload = mock_broadcast.call_args.args[0]
        assert broadcast_payload["type"] == "sensor_data"
        assert broadcast_payload["device_eui"] == eui

    def test_power_sensor_also_writes_legacy_table(self, admin_client, db, mocker):
        eui = "EEFF001122334455"
        insert_sensor(db, eui, sensor_type="power_3phase")

        mocker.patch("app.apis.lorawan_webhook.websocket_manager.broadcast", new_callable=AsyncMock)
        mocker.patch("app.apis.lorawan_webhook.decode_sensor_payload", return_value={
            "sensor_type": "power_3phase",
            "rms_amps": 20.0,
            "power_kw": 8.0,
            "max_amps": 22.0,
            "min_amps": 18.0
        })

        admin_client.post("/api/lorawan/webhook", json=make_webhook_body(sensor_eui=eui))

        row = db_fetchrow(db, "SELECT * FROM sensor_readings WHERE sensor_eui = $1", eui)
        assert row is not None
        assert float(row["rms_amps"]) == pytest.approx(20.0)