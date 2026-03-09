---
phase: 01-input-foundation
plan: 04
subsystem: payload-generation
tags: [tdd, payload-factory, uniqueness, lp-periodic]
requirements:
  provides: [INPUT-02, INPUT-03]
  affects: [INPUT-04]
tech-stack:
  added:
    - "uuid (stdlib) - UUID v4 generation for trxId"
  patterns:
    - "Factory pattern - PayloadFactory encapsulates payload generation logic"
    - "Uniqueness tracking - In-memory set for (meterId, samplingTime) pairs"
    - "Collision resolution - Incremental slot advancement on collision"
key-files:
  created:
    - path: "src/loadgen/payload.py"
      lines: 144
      purpose: "PayloadFactory with uniqueness guarantees"
    - path: "tests/test_payload_factory.py"
      tests: 8
      purpose: "Schema compliance and payload structure tests"
    - path: "tests/test_uniqueness.py"
      tests: 8
      purpose: "Uniqueness tracking and collision handling tests"
  modified: []
decisions: []
metrics:
  duration: "8 minutes"
  completed: "2026-03-09T12:42:00Z"
  commits: 2
  tests: "16/16 passing"
---

# Phase 1 Plan 4: Payload Factory Summary

**One-liner:** UUID-based payload factory with (meterId, samplingTime) uniqueness tracking and collision resolution using in-memory set tracking.

## Implementation Summary

Successfully implemented PayloadFactory for generating unique LP periodic payloads with guaranteed uniqueness constraints. The factory enforces uniqueness at two levels: per-message trxId (UUID v4) and per-run (meterId, samplingTime) pairs with automatic collision resolution.

## Key Features

### Payload Generation
- **UUID v4 trxId**: Each payload gets a unique transaction ID using `uuid.uuid4()`
- **Schema Compliance**: Full LP periodic envelope matching python-mqtt-benchmark.md spec
- **ISO 8601 Timestamps**: All timestamps use 'Z' suffix for UTC timezone
- **Placeholder Registers**: Phase 1 includes realistic but static register values (voltage, current, power)

### Uniqueness Guarantees
- **Per-Message Uniqueness**: Every payload has a unique UUID v4 trxId
- **Per-Run Uniqueness**: (meterId, samplingTime) pairs tracked in in-memory set
- **Collision Detection**: Automatic detection when pair already exists
- **Collision Resolution**: Increment slot_index by 15 minutes until unique
- **Collision Logging**: Warning logged when collision detected and resolved

### Integration Points
- **csv_reader**: Can load meter IDs for batch generation (via import)
- **slot_planner**: Uses SlotPlanner for 15-minute boundary timestamp generation
- **uuid (stdlib)**: Uses uuid.uuid4() for unique transaction IDs

## Technical Details

### Payload Structure
```python
{
    "trxId": "uuid-v4",
    "meterId": "12-char-meter-id",
    "dcuId": "DCU-001" (default, configurable),
    "operationType": "meterLoadProfilePeriodic",
    "operationResult": {
        "samplingTime": "ISO-8601-with-Z",
        "collectionTime": "samplingTime + 30s",
        "registers": {
            # Phase 1: Static placeholder values
            "voltageL1": 220.0,
            "currentL1": 5.0,
            "powerFactor": 0.95,
            # ... more registers
        }
    }
}
```

### Collision Handling Algorithm
1. Generate initial samplingTime using SlotPlanner.assign_slot(slot_index)
2. Check if (meter_id, sampling_time) in _seen_pairs
3. If collision: log warning, increment slot_index, recalculate samplingTime
4. Repeat until unique pair found
5. Add to _seen_pairs and return payload

### Uniqueness Scope
- **Per-Run Only**: Each PayloadFactory instance maintains separate _seen_pairs
- **No Cross-Run Tracking**: Different factories can generate same pairs
- **Same Meter, Different Times**: One meter can have multiple unique timestamps
- **Different Meters, Same Time**: Different meters can share same samplingTime

## Test Coverage

### Test Payload (8 tests)
1. ✓ trxId is valid UUID v4 format
2. ✓ All required fields present
3. ✓ Schema matches python-mqtt-benchmark.md spec
4. ✓ Custom meter ID is used
5. ✓ Custom sampling time via slot_index
6. ✓ collectionTime after samplingTime
7. ✓ Custom DCU ID support
8. ✓ Default DCU ID is DCU-001

### Test Uniqueness (8 tests)
1. ✓ No duplicate (meterId, samplingTime) pairs
2. ✓ Collision increments by 15 minutes
3. ✓ Uniqueness scope is per-run only
4. ✓ Multiple meters handled correctly
5. ✓ Uniqueness set properly initialized
6. ✓ Collisions are logged
7. ✓ Multiple sequential collisions handled
8. ✓ Different meters can use same slot

**Total**: 16/16 tests passing

## Deviations from Plan

**None** - Plan executed exactly as written.

### Test Implementation Notes
- **Test Fix**: Corrected test_different_meters_same_slot assertion logic
  - Original test incorrectly expected all times to be unique
  - Fixed to verify all times are identical (expected behavior for different meters using same slot)
  - This was a test logic bug, not a deviation from requirements

## Success Criteria Met

- ✓ src/loadgen/payload.py exists with PayloadFactory class (144 lines, >100 minimum)
- ✓ PayloadFactory generates payloads with all required fields
- ✓ Each payload has unique UUID v4 trxId
- ✓ (meterId, samplingTime) pairs are unique within a run
- ✓ Collisions increment samplingTime by 15 minutes with warning logged
- ✓ Payloads match python-mqtt-benchmark.md schema exactly
- ✓ All 16 tests pass (8 schema + 8 uniqueness)
- ✓ Can import via "from loadgen.payload import PayloadFactory"

## Commits

1. **0109694** - `test(01-04): add failing tests for payload factory and uniqueness tracking`
   - RED phase: Failing tests for schema and uniqueness requirements

2. **de9b46c** - `feat(01-04): implement payload factory with uniqueness tracking`
   - GREEN phase: Working implementation with all tests passing
   - 144 lines in payload.py (exceeds 100-line minimum)
   - 16/16 tests passing

## Next Steps

Phase 1 complete! Ready for Phase 2:
- Phase 2 will implement real LP data simulation (replacing placeholder register values)
- Full 96 slots/day/meter scenario
- Mixed LP/Instantaneous/EOB payloads
- MQTT publisher implementation

## Self-Check: PASSED

- ✓ Created files exist:
  - src/loadgen/payload.py (144 lines)
  - tests/test_payload_factory.py (8 tests)
  - tests/test_uniqueness.py (8 tests)
- ✓ Commits verified: 0109694, de9b46c
- ✓ All tests passing: 16/16
- ✓ Integration points verified: csv_reader, slot_planner, uuid
- ✓ Schema compliance verified against python-mqtt-benchmark.md
- ✓ Uniqueness guarantees verified
- ✓ Collision handling verified
- ✓ ISO 8601 timestamps verified

---

*Plan completed: 2026-03-09*
*TDD approach: RED → GREEN → (no REFACTOR needed)*
*Phase 1 Input Foundation: 4 of 4 plans complete (100%)*
