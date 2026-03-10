---
created: 2026-03-10T23:10:33.620Z
title: Add custom date for sampling_time in YAML scenario
area: general
files:
  - scenarios/*.yaml
  - src/loadgen/slot_planner.py:26-38
  - src/loadgen/publisher.py
---

## Problem

Currently, `SlotPlanner.__init__()` uses `datetime.now(timezone.utc)` as the default base_time when no base_time is provided. This means loadgen benchmarks always run with "today's" date for sampling_time values.

For testing purposes (e.g., simulating historical data, reproducing specific date scenarios, or testing date-based business logic), users need the ability to specify a custom start date in the scenario YAML file.

## Solution

Add an optional `base_time` or `start_date` parameter to the scenario YAML schema:

```yaml
payload:
  dcu_id: DCUX001
  meter_id_source: ../Asset-Meter.csv
  base_time: "2026-03-11T00:00:00Z"  # Optional: custom start date
```

Implementation approach:
1. Update `src/loadgen/config.py` schema to include optional `base_time` field
2. Pass `base_time` from CLI → Config → Publisher → SlotPlanner
3. Parse ISO 8601 datetime string from YAML
4. Maintain backward compatibility (default to current UTC time if not specified)
