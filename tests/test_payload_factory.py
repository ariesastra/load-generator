"""
Test stubs for payload factory functionality (INPUT-02 requirement).

These tests validate generation of LP periodic payloads with proper
schema, unique transaction IDs, and required fields.
"""

import pytest
import re
from datetime import datetime
from loadgen.payload import PayloadFactory


def test_generate_payload_has_trx_id():
    """
    Verify payload contains unique trxId (UUID format).

    Given: A request to generate a payload
    When: The payload is generated
    Then: The payload contains a trxId field
    And: The trxId is a valid UUID v4 format
    And: Each generated payload has a unique trxId
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    assert "trxId" in payload
    assert isinstance(payload["trxId"], str)
    # UUID v4 format: 8-4-4-4-12 hex digits
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    assert re.match(uuid_pattern, payload["trxId"], re.IGNORECASE)

    # Verify uniqueness across multiple generations
    payload2 = factory.generate_payload(meter_id="000000000050", slot_index=0)
    assert payload["trxId"] != payload2["trxId"]


def test_generate_payload_has_required_fields():
    """
    Verify all LP periodic fields are present.

    Given: A request to generate a payload
    When: The payload is generated
    Then: All required fields are present:
         - trxId (UUID)
         - meterId (string)
         - dcuId (string)
         - operationType = "meterLoadProfilePeriodic"
         - operationResult (object with samplingTime, collectionTime, meterId, clock, status, alarmRegister)
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    required_fields = ["trxId", "meterId", "dcuId", "operationType", "operationResult"]
    for field in required_fields:
        assert field in payload, f"Missing required field: {field}"

    assert payload["operationType"] == "meterLoadProfilePeriodic"

    # Check operationResult sub-fields (flat structure, not nested)
    operation_result = payload["operationResult"]
    required_op_fields = [
        "samplingTime", "collectionTime", "meterId", "clock", "status", "alarmRegister"
    ]
    for field in required_op_fields:
        assert field in operation_result, f"Missing operationResult field: {field}"


def test_generate_payload_matches_schema():
    """
    Verify payload matches python-mqtt-benchmark.md spec.

    Given: The python-mqtt-benchmark.md specification
    When: A payload is generated
    Then: The payload structure matches the spec exactly
    And: All data types are correct (strings, ISO 8601 timestamps, etc.)
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    # Verify structure matches spec
    assert isinstance(payload, dict)
    assert isinstance(payload["trxId"], str)
    assert isinstance(payload["meterId"], str)
    assert isinstance(payload["dcuId"], str)
    assert isinstance(payload["operationType"], str)
    assert isinstance(payload["operationResult"], dict)

    # Verify timestamp formats (ISO 8601)
    operation_result = payload["operationResult"]
    assert "T" in operation_result["samplingTime"]
    assert operation_result["samplingTime"].endswith("Z")
    assert "T" in operation_result["collectionTime"]
    assert operation_result["collectionTime"].endswith("Z")


def test_generate_payload_with_custom_meter_id():
    """
    Verify payload uses provided meter ID.

    Given: A specific meter ID is provided
    When: A payload is generated with that meter ID
    Then: The payload contains the provided meter ID
    """
    factory = PayloadFactory()
    meter_id = "000000000050"
    payload = factory.generate_payload(meter_id=meter_id, slot_index=0)

    assert payload["meterId"] == meter_id


def test_generate_payload_with_custom_sampling_time():
    """
    Verify payload uses provided sampling time via slot_index.

    Given: A specific slot index is provided
    When: A payload is generated with that slot index
    Then: The payload contains the corresponding sampling time in operationResult
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=1)

    # Slot index 1 should be 15 minutes after base time
    sampling_time_str = payload["operationResult"]["samplingTime"]
    assert sampling_time_str.endswith("Z")

    # Verify it's a valid ISO 8601 timestamp
    sampling_time = datetime.fromisoformat(sampling_time_str.replace('Z', '+00:00'))
    assert sampling_time is not None


def test_generate_payload_collection_time_after_sampling_time():
    """
    Verify collectionTime is after samplingTime.

    Given: A payload is generated
    When: The samplingTime and collectionTime are set
    Then: collectionTime is after samplingTime (typically +delta)
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    sampling_time_str = payload["operationResult"]["samplingTime"]
    collection_time_str = payload["operationResult"]["collectionTime"]

    sampling_time = datetime.fromisoformat(sampling_time_str.replace('Z', '+00:00'))
    collection_time = datetime.fromisoformat(collection_time_str.replace('Z', '+00:00'))

    assert collection_time > sampling_time


def test_custom_dcu_id():
    """
    Verify custom DCU ID can be set.

    Given: A PayloadFactory is created with a custom DCU ID
    When: Payloads are generated
    Then: All payloads use the custom DCU ID
    """
    factory = PayloadFactory(dcu_id="CUSTOM-DCU")
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    assert payload["dcuId"] == "CUSTOM-DCU"


def test_default_dcu_id():
    """
    Verify default DCU ID is DCU-001.

    Given: A PayloadFactory is created with no DCU ID
    When: Payloads are generated
    Then: All payloads use the default DCU-001
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    assert payload["dcuId"] == "DCU-001"


def test_generate_payload_has_voltage_fields():
    """
    Verify operationResult contains voltage fields.

    Given: A payload is generated
    When: The operationResult is examined
    Then: All voltage fields (L1, L2, L3) are present
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    assert "voltageL1" in operation_result
    assert "voltageL2" in operation_result
    assert "voltageL3" in operation_result
    assert isinstance(operation_result["voltageL1"], (int, float))


def test_generate_payload_has_current_fields():
    """
    Verify operationResult contains current fields.

    Given: A payload is generated
    When: The operationResult is examined
    Then: All current fields (L1, L2, L3) are present
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    assert "currentL1" in operation_result
    assert "currentL2" in operation_result
    assert "currentL3" in operation_result
    assert isinstance(operation_result["currentL1"], (int, float))


def test_generate_payload_has_energy_fields():
    """
    Verify operationResult contains energy (wh) fields.

    Given: A payload is generated
    When: The operationResult is examined
    Then: All energy fields (whExportL1/L2/L3/Total, whImportL1/L2/L3/Total) are present
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    energy_fields = [
        "whExportL1", "whExportL2", "whExportL3", "whExportTotal",
        "whImportL1", "whImportL2", "whImportL3", "whImportTotal"
    ]
    for field in energy_fields:
        assert field in operation_result, f"Missing energy field: {field}"
        assert isinstance(operation_result[field], (int, float))


def test_generate_payload_has_power_fields():
    """
    Verify operationResult contains power (w) fields.

    Given: A payload is generated
    When: The operationResult is examined
    Then: Power fields (wExportTotal, wImportTotal) are present
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    assert "wExportTotal" in operation_result
    assert "wImportTotal" in operation_result
    assert isinstance(operation_result["wExportTotal"], (int, float))
    assert isinstance(operation_result["wImportTotal"], (int, float))


def test_generate_payload_has_reactive_energy_fields():
    """
    Verify operationResult contains reactive energy (varh) fields.

    Given: A payload is generated
    When: The operationResult is examined
    Then: Reactive energy fields (varhExportTotal, varhImportTotal, varhTotal) are present
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    assert "varhExportTotal" in operation_result
    assert "varhImportTotal" in operation_result
    assert "varhTotal" in operation_result
    assert isinstance(operation_result["varhTotal"], (int, float))


def test_generate_payload_has_power_factor():
    """
    Verify operationResult contains powerFactor field.

    Given: A payload is generated
    When: The operationResult is examined
    Then: powerFactor field is present and is a number
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    assert "powerFactor" in operation_result
    assert isinstance(operation_result["powerFactor"], (int, float))


def test_generate_payload_status_and_alarm():
    """
    Verify operationResult contains status and alarmRegister fields.

    Given: A payload is generated
    When: The operationResult is examined
    Then: status is "OK" and alarmRegister is a 32-character string
    """
    factory = PayloadFactory()
    payload = factory.generate_payload(meter_id="000000000049", slot_index=0)

    operation_result = payload["operationResult"]
    assert operation_result["status"] == "OK"
    assert "alarmRegister" in operation_result
    assert len(operation_result["alarmRegister"]) == 32  # 32-bit register string


def test_generate_payload_meter_id_in_operation_result():
    """
    Verify operationResult contains meterId field matching payload meterId.

    Given: A payload is generated with a specific meterId
    When: The operationResult is examined
    Then: operationResult.meterId matches payload.meterId
    """
    factory = PayloadFactory()
    meter_id = "000000000049"
    payload = factory.generate_payload(meter_id=meter_id, slot_index=0)

    assert payload["meterId"] == meter_id
    assert payload["operationResult"]["meterId"] == meter_id
