import pytest
import asyncio
import uuid
from datetime import datetime, timedelta

import app.libs.database as db_mod
from app.libs.database import (
    insert_sensor_reading,
    get_sensor_readings,
    get_latest_readings_by_machine,
    get_readings_for_timerange,
    cleanup_old_readings,
)
from app.libs.models import SensorReading, PowerConsumptionQuery


def make_sensor_reading(**kwargs) -> SensorReading:
    return SensorReading(
        sensor_eui=kwargs.get("sensor_eui", f"EUI-{uuid.uuid4().hex[:8]}"),
        machine_name=kwargs.get("machine_name", "Test Machine"),
        timestamp=kwargs.get("timestamp", datetime.now()),
        rms_amps=kwargs.get("rms_amps", 10.0),
        max_amps=kwargs.get("max_amps", 12.0),
        min_amps=kwargs.get("min_amps", 8.0),
        amp_hour_accumulation=kwargs.get("amp_hour_accumulation", 100.0),
        capacitor_voltage=kwargs.get("capacitor_voltage", 3.7),
        temperature=kwargs.get("temperature", 25.0),
        signal_strength=kwargs.get("signal_strength", -80),
        battery_status=kwargs.get("battery_status", "100"),
        raw_payload=kwargs.get("raw_payload", bytes.fromhex("deadbeef")),
    )


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        db_mod._connection_pool = None
        loop.close()


class TestInsertAndRetrieveSensorReading:

    def test_insert_returns_id(self):
        record_id = run(insert_sensor_reading(make_sensor_reading()))
        assert isinstance(record_id, int)

    def test_inserted_reading_is_retrievable(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, rms_amps=5.0))
            return await get_sensor_readings(PowerConsumptionQuery(sensor_euis=[eui], limit=10))

        results = run(_test())
        assert len(results) == 1
        assert results[0].sensor_eui == eui
        assert results[0].rms_amps == 5.0

    def test_power_kw_is_calculated_correctly(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"
        rms_amps = 10.0
        expected_power_kw = (400 * rms_amps * 1.732) / 1000

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, rms_amps=rms_amps))
            return await get_sensor_readings(PowerConsumptionQuery(sensor_euis=[eui], limit=10))

        results = run(_test())
        assert abs(results[0].power_kw - expected_power_kw) < 0.001


class TestGetSensorReadingsFiltering:

    def test_filter_by_sensor_eui(self):
        eui_a = f"EUI-{uuid.uuid4().hex[:8]}"
        eui_b = f"EUI-{uuid.uuid4().hex[:8]}"

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui_a))
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui_b))
            return await get_sensor_readings(PowerConsumptionQuery(sensor_euis=[eui_a], limit=10))

        results = run(_test())
        assert all(r.sensor_eui == eui_a for r in results)

    def test_filter_by_time_range(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"
        old_time = datetime.now() - timedelta(days=10)
        new_time = datetime.now()

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=old_time))
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=new_time))
            return await get_sensor_readings(PowerConsumptionQuery(
                sensor_euis=[eui],
                start_time=datetime.now() - timedelta(days=1),
                limit=10,
            ))

        results = run(_test())
        assert len(results) == 1

    def test_limit_is_respected(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"

        async def _test():
            for _ in range(5):
                await insert_sensor_reading(make_sensor_reading(sensor_eui=eui))
            return await get_sensor_readings(PowerConsumptionQuery(sensor_euis=[eui], limit=3))

        results = run(_test())
        assert len(results) == 3


class TestGetLatestReadingsByMachine:

    def test_returns_latest_reading_per_sensor(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"
        older = datetime.now() - timedelta(hours=2)
        newer = datetime.now()

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=older, rms_amps=1.0))
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=newer, rms_amps=9.0))
            return await get_latest_readings_by_machine()

        result = run(_test())
        assert eui in result
        assert result[eui].rms_amps == 9.0


class TestGetReadingsForTimerange:

    def test_returns_readings_within_hours(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=datetime.now()))
            return await get_readings_for_timerange(sensor_euis=[eui], hours_back=1)

        results = run(_test())
        assert len(results) >= 1

    def test_excludes_readings_outside_range(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"
        old_time = datetime.now() - timedelta(hours=48)

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=old_time))
            return await get_readings_for_timerange(sensor_euis=[eui], hours_back=1)

        results = run(_test())
        assert len(results) == 0


class TestCleanupOldReadings:

    def test_deletes_old_records(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"
        old_time = datetime.now() - timedelta(days=60)

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=old_time))
            deleted = await cleanup_old_readings(days_to_keep=30)
            results = await get_sensor_readings(PowerConsumptionQuery(sensor_euis=[eui], limit=10))
            return deleted, results

        deleted, results = run(_test())
        assert deleted >= 1
        assert len(results) == 0

    def test_keeps_recent_records(self):
        eui = f"EUI-{uuid.uuid4().hex[:8]}"

        async def _test():
            await insert_sensor_reading(make_sensor_reading(sensor_eui=eui, timestamp=datetime.now()))
            await cleanup_old_readings(days_to_keep=30)
            return await get_sensor_readings(PowerConsumptionQuery(sensor_euis=[eui], limit=10))

        results = run(_test())
        assert len(results) == 1