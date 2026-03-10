---
status: awaiting_human_verify
trigger: "slot-planner-30min-gap"
created: 2026-03-11T00:00:00Z
updated: 2026-03-11T00:05:00Z
---

## Current Focus
hypothesis: Round-robin meter distribution with shared slot_index sequence causes per-meter 30-minute gaps
test: verified with test_meter_filter.py - filtering to one meter shows 30-minute gaps
expecting: each meter gets every other slot_index (0,2,4,... or 1,3,5,...), creating 30-minute gaps
next_action: determine if this is by design or if slot_index should be per-meter

## Symptoms
expected: 96 messages with 15-minute gaps between sampling_time values
actual: 91 messages with 30-minute gaps (e.g., 22:00:00Z → 22:30:00Z instead of → 22:15:00Z)
errors: None (no error messages, just wrong data)
reproduction: Run benchmark with scenarios/scenario_1k.yaml (message_count=96, worker_count=2, rate_limit=100)
timeline: Just discovered - user observed payload events and noticed 30-minute gaps despite slot_planner.py having 15-minute logic

## Eliminated

## Evidence

- timestamp: 2026-03-11T00:00:00Z
  checked: Publisher._generate_payloads() method (lines 212-245)
  found: slot_index increments by 1 for each message: `slot_index += 1` (line 243)
  implication: slot_index correctly increments 0, 1, 2, 3, ... for 96 messages

- timestamp: 2026-03-11T00:00:00Z
  checked: Publisher._generate_payloads() meter distribution (line 235)
  found: Round-robin distribution: `meter_id = self._meter_ids[i % len(self._meter_ids)]`
  implication: If there are fewer meter IDs than messages, meters are reused

- timestamp: 2026-03-11T00:00:00Z
  checked: PayloadFactory.generate_payload() collision detection (lines 84-92)
  found: When (meter_id, sampling_time) already exists, slot_index increments until unique
  implication: THIS IS THE BUG - reusing meters causes collision detection to skip slots

- timestamp: 2026-03-11T00:01:00Z
  checked: Created test_slot_debug.py to reproduce issue
  found: Generated 96 messages with unique sampling_times, all 15-minute gaps
  implication: SlotPlanner and PayloadFactory are working correctly - bug is elsewhere

- timestamp: 2026-03-11T00:02:00Z
  checked: Created test_meter_filter.py to simulate filtering by one meter
  found: When filtered to one meter with 2 meters total, shows 48 messages with 30-minute gaps
  implication: ROOT CAUSE FOUND - round-robin distribution means each meter gets every other slot_index

- timestamp: 2026-03-11T00:03:00Z
  checked: Publisher._generate_payloads() round-robin logic (line 235)
  found: meter_id = self._meter_ids[i % len(self._meter_ids)]
  implication: With 2 meters, meter[0] gets slots 0,2,4,... and meter[1] gets slots 1,3,5,...

- timestamp: 2026-03-11T00:04:00Z
  checked: SlotPlanner.assign_slot() logic (line 56)
  found: timestamp = base_time + timedelta(minutes=slot_index * 15)
  implication: slot_index=2 → 30 minutes, slot_index=4 → 60 minutes, etc.

## Resolution
root_cause: Publisher._generate_payloads() uses a global slot_index counter that increments for all messages. With round-robin meter distribution, each meter gets every other slot_index (e.g., meter[0] gets 0,2,4,... and meter[1] gets 1,3,5,...). This causes per-meter sampling_time gaps of 30 minutes instead of 15 minutes.

fix: Changed Publisher._generate_payloads() to track slot_index PER-METER instead of globally.
- Before: `slot_index = 0` then `slot_index += 1` for all messages
- After: `slot_indices = {meter_id: 0 for meter_id in self._meter_ids}` then `slot_indices[meter_id] += 1`
- This ensures each meter gets consecutive 15-minute slots

verification: Created test_fix_two_meters.py and test_collision_detection.py to verify:
- With 2 meters and 20 messages: each meter gets 10 messages with 15-minute gaps ✓
- Collision detection still works correctly ✓
- No duplicate (meterId, samplingTime) pairs ✓

files_changed:
- src/loadgen/publisher.py: Changed _generate_payloads() to use per-meter slot_indices dict
- tests/test_publisher_slot_distribution.py: Added regression tests for per-meter slot tracking
