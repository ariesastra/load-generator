---
created: 2026-03-10T13:53:41.124Z
title: Update PayloadFactory loadprofile schema to match production format
area: api
files:
  - src/loadgen/payload.py:103-125
---

## Problem

The PayloadFactory in `src/loadgen/payload.py` generates a loadprofile schema that differs from the actual production payload format. Current implementation uses:

```python
"operationResult": {
    "samplingTime": "...",
    "collectionTime": "...",
    "registers": {
        "voltageL1": 220.0,
        "currentL1": 5.0,
        "powerFactor": 0.95,
        # etc...
    }
}
```

But production payload has a flatter structure with additional fields:

```json
"operationResult": {
    "samplingTime": "2026-02-24T00:00:00+07:00",
    "collectionTime": "2026-02-24T00:00:00+07:00",
    "meterId": "4440229",
    "clock": "2026-02-24T00:00:00+07:00",
    "status": "OK",
    "alarmRegister": "00000000000000000000100000000000",
    "voltageL1": 130.5,
    "voltageL2": 230.5,
    "voltageL3": 330.5,
    "currentL1": 10.1,
    "currentL2": 20.2,
    "currentL3": 30.3,
    "whExportL1": 100.1,
    "whExportL2": 200.1,
    "whExportL3": 300.1,
    "whExportTotal": 500.1,
    "whImportL1": 400.1,
    "whImportL2": 500.1,
    "whImportL3": 600.1,
    "whImportTotal": 1500.1,
    "wExportTotal": 10.5,
    "wImportTotal": 100.2,
    "varhExportTotal": 1.2,
    "varhImportTotal": 1.6,
    "varhTotal": 10.2,
    "powerFactor": 0.9
}
```

Key differences:
1. Fields are directly in `operationResult`, not nested under `registers`
2. Additional fields: `meterId`, `clock`, `status`, `alarmRegister`
3. Energy fields: `whExportL1/L2/L3/Total`, `whImportL1/L2/L3/Total`
4. Power fields: `wExportTotal`, `wImportTotal`
5. Reactive energy: `varhExportTotal`, `varhImportTotal`, `varhTotal`

## Solution

Update `PayloadFactory.generate_payload()` in `src/loadgen/payload.py` (lines 103-125) to match production schema:

1. Flatten `registers` fields directly into `operationResult`
2. Add missing fields: `meterId`, `clock`, `status`, `alarmRegister`
3. Add all energy/power fields from production format
4. Update tests in `tests/test_payload_factory.py` accordingly
5. Consider making values configurable for realistic load generation
