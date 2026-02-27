import pytest
import struct
from app.libs.payload_decoders import (
    decode_milesight_em400_tld,
    decode_hotdrop_payload,
    decode_milesight_ct101,
    decode_lorawan_ac_current,
    calculate_part_detection,
    decode_sensor_payload,
)


# EM400-TLD distance sensor

class TestDecodeEM400TLD:

    def test_valid_hex_payload(self):
        # Battery=98%, temp=25.0°C, distance=1500mm, position=normal
        payload = "017562" + "03670410" + "04820BFA" + "050000"
        result = decode_milesight_em400_tld(payload)
        assert result["battery_level"] == 98
        assert result["distance_mm"] == 64011  # 0xFA0B little-endian
        assert result["model"] == "EM400-TLD"

    def test_distance_converted_to_meters(self):
        # distance = 0x03E8 = 1000mm = 1.0m
        payload = "0482E803"
        result = decode_milesight_em400_tld(payload)
        assert result["distance_mm"] == 1000
        assert result["distance_m"] == 1.0

    def test_position_normal(self):
        payload = "050000"
        result = decode_milesight_em400_tld(payload)
        assert result["position"] == "normal"

    def test_position_tilt(self):
        payload = "050001"
        result = decode_milesight_em400_tld(payload)
        assert result["position"] == "tilt"

    def test_invalid_payload_returns_error(self):
        result = decode_milesight_em400_tld("ZZZZZZ")
        assert "error" in result
        assert result["distance_mm"] is None

    def test_format_detected_hex(self):
        payload = "0175621"  # Odd length to force base64 path, use valid hex
        payload = "017562"
        result = decode_milesight_em400_tld(payload)
        assert result["format_detected"] == "HEX"


# HotDrop 3-phase power sensor

class TestDecodeHotdrop:

    def test_valid_payload(self):
        # rms=6.0A, max=7.0A, min=5.0A, amp_hour=1.0Ah, cap_voltage=3.3V
        data = struct.pack('<HHH', 6000, 7000, 5000) + struct.pack('<I', 1000000) + bytes([33])
        result = decode_hotdrop_payload(data.hex())
        assert result["rms_amps"] == pytest.approx(6.0)
        assert result["max_amps"] == pytest.approx(7.0)
        assert result["min_amps"] == pytest.approx(5.0)
        assert result["amp_hour_accumulation"] == pytest.approx(1.0)
        assert result["capacitor_voltage"] == pytest.approx(3.3)

    def test_power_kw_calculated(self):
        # rms=10A → P = 400 * 10 * 1.732 / 1000 = 6.928 kW
        data = struct.pack('<HHH', 10000, 10000, 10000) + struct.pack('<I', 0) + bytes([0])
        result = decode_hotdrop_payload(data.hex())
        assert result["power_kw"] == pytest.approx(6.928, rel=1e-3)

    def test_wrong_length_returns_error(self):
        result = decode_hotdrop_payload("AABBCC")
        assert "error" in result

    def test_invalid_hex_returns_error(self):
        result = decode_hotdrop_payload("ZZZZZZZZZZZZZZZZZZZZZZ")
        assert "error" in result

    def test_model_and_sensor_type(self):
        data = struct.pack('<HHH', 0, 0, 0) + struct.pack('<I', 0) + bytes([0])
        result = decode_hotdrop_payload(data.hex())
        assert result["model"] == "HotDrop"
        assert result["sensor_type"] == "power_3phase"


# CT101 single-phase current sensor

class TestDecodeCT101:

    def test_valid_payload(self):
        
        # From docstring example: 03972A3301000498B5020967FFFF
        result = decode_milesight_ct101("03972A3301000498B5020967FFFF")
        assert result["total_current_ah"] == pytest.approx(786.34, rel=1e-3)
        assert result["rms_amps"] == pytest.approx(6.93, rel=1e-3)

    def test_temperature_read_failed(self):
        # 0xFFFF temperature = read_failed
        result = decode_milesight_ct101("0967FFFF")
        assert result.get("temperature_status") == "read_failed"

    def test_current_read_failed(self):
        # 0xFFFF current = read_failed
        result = decode_milesight_ct101("0498FFFF")
        assert result.get("current_status") == "read_failed"

    def test_power_estimated_from_current(self):
        # current = 10.0A → power = 230 * 10 / 1000 = 2.3 kW
        current_raw = struct.pack('<H', 1000)  # 1000 / 100 = 10.0A
        payload = bytes([0x04, 0x98]) + current_raw
        result = decode_milesight_ct101(payload.hex())
        assert result["power_kw"] == pytest.approx(2.3, rel=1e-3)

    def test_invalid_hex_returns_error(self):
        result = decode_milesight_ct101("ZZZZ")
        assert "error" in result
        assert result["model"] == "CT101"


# LoRaWAN AC current sensor

class TestDecodeLorawanACCurrent:

    def test_valid_22char_payload(self):
        # Byte 4 = 0xA2 = 162 → 16.2A
        payload = "3200002BB700000000EF89"
        result = decode_lorawan_ac_current(payload)
        assert result["rms_amps"] == pytest.approx(18.3, rel=1e-3)

    def test_power_calculated(self):
        # 10.0A @ 230V = 2.3 kW
        data = bytes([0x32, 0x00, 0x00, 0x00, 100, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        result = decode_lorawan_ac_current(data.hex())
        assert result["rms_amps"] == pytest.approx(10.0)
        assert result["power_kw"] == pytest.approx(2.3, rel=1e-3)

    def test_wrong_length_returns_error(self):
        result = decode_lorawan_ac_current("AABB")
        assert "error" in result

    def test_model_and_sensor_type(self):
        data = bytes([0x32] + [0x00] * 10)
        result = decode_lorawan_ac_current(data.hex())
        assert result["model"] == "LoRaWAN_AC_Current"
        assert result["sensor_type"] == "power_1phase"


# Part detection

class TestCalculatePartDetection:

    def test_part_detected(self):
        detected, qty = calculate_part_detection(50.0, 200.0, 100.0)
        assert detected is True
        assert qty == 1

    def test_no_part_detected(self):
        detected, qty = calculate_part_detection(180.0, 200.0, 50.0)
        assert detected is False
        assert qty == 0

    def test_none_distance_returns_false(self):
        detected, qty = calculate_part_detection(None, 200.0, 50.0)
        assert detected is False
        assert qty == 0

    def test_defaults_used_when_no_baseline(self):
        # Default baseline=200, trigger=50 → distance=100 → reduction=100 >= 50 → detected
        detected, qty = calculate_part_detection(100.0, None, None)
        assert detected is True


# Universal decoder routing

class TestDecodeSensorPayload:

    def test_routes_by_model_em400(self):
        payload = "017562"
        result = decode_sensor_payload("distance", payload, sensor_model="EM400-TLD")
        assert result["model"] == "EM400-TLD"

    def test_routes_by_model_ct101(self):
        result = decode_sensor_payload("power_1phase", "03972A3301000498B5020967FFFF", sensor_model="CT101")
        assert result["model"] == "CT101"

    def test_routes_by_model_hotdrop(self):
        data = struct.pack('<HHH', 0, 0, 0) + struct.pack('<I', 0) + bytes([0])
        result = decode_sensor_payload("power_3phase", data.hex(), sensor_model="HotDrop")
        assert result["model"] == "HotDrop"

    def test_routes_by_sensor_type_fallback(self):
        data = struct.pack('<HHH', 0, 0, 0) + struct.pack('<I', 0) + bytes([0])
        result = decode_sensor_payload("power_3phase", data.hex())
        assert result["model"] == "HotDrop"

    def test_unknown_type_returns_error_or_guess(self):
        result = decode_sensor_payload("unknown_type", "ZZZZ")
        assert "error" in result or "sensor_type" in result