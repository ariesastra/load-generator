---
phase: quick
plan: 1
type: execute
wave: 1
depends_on: []
files_modified:
  - src/loadgen/config.py
  - src/loadgen/publisher.py
  - src/loadgen/payload.py
autonomous: true
requirements:
  - CUSTOM_DATE_001: Add optional base_time parameter to YAML scenario
  - CUSTOM_DATE_002: Parse ISO 8601 datetime from YAML configuration
  - CUSTOM_DATE_003: Pass base_time through CLI → Config → Publisher → SlotPlanner
  - CUSTOM_DATE_004: Maintain backward compatibility (default to current UTC time)

must_haves:
  truths:
    - "User can specify custom base_time in YAML scenario file"
    - "Scenario without base_time uses current UTC time (backward compatible)"
    - "base_time is parsed from ISO 8601 format in YAML"
    - "base_time flows from Config → Publisher → SlotPlanner → PayloadFactory"
    - "sampling_time in generated payloads uses custom base_time"

  artifacts:
    - path: "src/loadgen/config.py"
      provides: "PayloadConfig.base_time field and ISO 8601 parsing"
      contains: "base_time: Optional[str]"
    - path: "src/loadgen/publisher.py"
      provides: "base_time parameter passed to PayloadFactory"
      contains: "base_time: Optional[datetime]"
    - path: "src/loadgen/payload.py"
      provides: "base_time passed to SlotPlanner"
      contains: "SlotPlanner(base_time=base_time)"

  key_links:
    - from: "scenarios/*.yaml"
      to: "PayloadConfig"
      via: "YAML parsing in load_config()"
      pattern: "payload_data.get\\('base_time'\\)"
    - from: "PayloadConfig"
      to: "Publisher"
      via: "ScenarioConfig.payload.base_time"
      pattern: "config.payload.base_time"
    - from: "Publisher"
      to: "PayloadFactory"
      via: "__init__ parameter"
      pattern: "base_time.*parameter"
    - from: "PayloadFactory"
      to: "SlotPlanner"
      via: "__init__ parameter"
      pattern: "SlotPlanner\\(base_time=\\)"
---

<objective>
Add custom date support for sampling_time in YAML scenario configuration.

**Purpose:** Enable users to simulate historical data or test date-based business logic by specifying a custom start date in scenario YAML files.

**Output:**
- Optional `base_time` field in YAML payload section
- ISO 8601 datetime parsing with backward compatibility
- base_time flow: Config → Publisher → PayloadFactory → SlotPlanner
</objective>

<execution_context>
@/Users/ariesastra/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ariesastra/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/todos/pending/2026-03-10-add-custom-date-for-sampling-time-in-yaml-scenario.md
@.planning/STATE.md

# Current Implementation

From src/loadgen/config.py:
```python
@dataclass
class PayloadConfig:
    dcu_id: str = "DCU-001"
    meter_id_source: Optional[str] = None

# In load_config():
payload_config = PayloadConfig(
    dcu_id=payload_data.get("dcu_id", "DCU-001"),
    meter_id_source=payload_data.get("meter_id_source"),
)
```

From src/loadgen/slot_planner.py:
```python
def __init__(self, base_time: Optional[datetime] = None):
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    self.base_time = self._round_to_15_min_boundary(base_time)
```

From src/loadgen/publisher.py:
```python
# Initialize payload factory
self._payload_factory = PayloadFactory(dcu_id=dcu_id)
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add base_time to PayloadConfig schema</name>
  <files>src/loadgen/config.py</files>
  <action>
Add base_time field to PayloadConfig dataclass:

1. Add field to PayloadConfig:
   - base_time: Optional[str] = None
   - Store as ISO 8601 string from YAML (e.g., "2026-03-11T00:00:00Z")

2. Add validation in __post_init__():
   - If base_time is provided, parse ISO 8601 format
   - Validate it's a valid datetime string
   - Raise ConfigValidationError if invalid

3. Update load_config() function:
   - Extract base_time from payload_data: payload_data.get("base_time")
   - Pass to PayloadConfig constructor

4. Add property to convert to datetime:
   - Add get_base_time_datetime() method that returns Optional[datetime]
   - Parse ISO 8601 string using datetime.fromisoformat()
   - Handle 'Z' suffix (replace with +00:00 for fromisoformat)

Do NOT use dateparser library — use stdlib datetime.fromisoformat() only.
Maintain backward compatibility: base_time defaults to None.
  </action>
  <verify>
    <automated>python -m pytest tests/test_config.py -v -k base_time</automated>
  </verify>
  <done>
    - PayloadConfig has base_time field
    - ISO 8601 strings parsed correctly
    - Invalid strings raise ConfigValidationError
    - None value is accepted (backward compatible)
    - get_base_time_datetime() returns datetime or None
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire base_time through Publisher and PayloadFactory</name>
  <files>src/loadgen/publisher.py, src/loadgen/payload.py</files>
  <action>
Pass base_time from config through Publisher to PayloadFactory to SlotPlanner:

1. Update Publisher.__init__():
   - Add base_time: Optional[datetime] = None parameter
   - Store as self._base_time = base_time

2. Update Publisher payload factory initialization:
   - Pass base_time to PayloadFactory: PayloadFactory(dcu_id=dcu_id, base_time=base_time)

3. Update PayloadFactory.__init__() in src/loadgen/payload.py:
   - Add base_time: Optional[datetime] = None parameter
   - Store as self._base_time = base_time

4. Update PayloadFactory._get_planner() or SlotPlanner initialization:
   - Pass base_time to SlotPlanner: SlotPlanner(base_time=self._base_time)

5. In CLI (src/loadgen/cli.py), when creating Publisher:
   - Parse base_time from config: base_time = config.payload.get_base_time_datetime()
   - Pass to Publisher constructor

Flow: YAML → PayloadConfig.base_time (str) → get_base_time_datetime() → Publisher.base_time (datetime) → PayloadFactory.base_time → SlotPlanner.base_time
  </action>
  <verify>
    <automated>python -m pytest tests/test_publisher.py -v -k base_time</automated>
  </verify>
  <done>
    - base_time flows from config to Publisher
    - Publisher passes base_time to PayloadFactory
    - PayloadFactory passes base_time to SlotPlanner
    - CLI reads base_time from config and passes to Publisher
    - Backward compatible: None values work throughout chain
  </done>
</task>

<task type="auto">
  <name>Task 3: Add integration test for custom base_time</name>
  <files>tests/test_config.py, tests/test_publisher.py</files>
  <action>
Add tests to verify base_time functionality:

1. Add test_config.py tests:
   - test_payload_config_with_base_time(): Valid ISO 8601 string
   - test_payload_config_invalid_base_time(): Invalid string raises error
   - test_payload_config_without_base_time(): None is accepted
   - test_get_base_time_datetime(): Converts string to datetime correctly
   - test_get_base_time_datetime_handles_z_suffix(): Parses "2026-03-11T00:00:00Z"

2. Add test_publisher.py integration test:
   - test_publisher_with_custom_base_time(): Publisher receives base_time
   - test_generated_payloads_use_custom_base_time(): sampling_time uses custom date

3. Create test scenario YAML with base_time:
   - scenarios/test_custom_base_time.yaml
   - Include base_time: "2026-03-11T00:00:00Z" in payload section

Tests should use pytest fixtures and follow existing test patterns in the codebase.
  </action>
  <verify>
    <automated>python -m pytest tests/test_config.py tests/test_publisher.py -v</automated>
  </verify>
  <done>
    - All base_time tests pass
    - Integration test verifies end-to-end flow
    - Test scenario file created
    - Edge cases covered (None, invalid, Z suffix)
  </done>
</task>

</tasks>

<verification>
1. Run all tests: `python -m pytest tests/ -v`
2. Test with scenario file containing base_time: `python -m loadgen.cli scenarios/scenario_1k.yaml --dry-run`
3. Verify sampling_time in generated payloads uses custom base_time
4. Test backward compatibility: run with scenario without base_time
</verification>

<success_criteria>
1. Users can specify `base_time: "2026-03-11T00:00:00Z"` in YAML payload section
2. Generated payloads use custom base_time for sampling_time values
3. Scenarios without base_time work exactly as before (backward compatible)
4. All existing tests still pass
5. New tests cover base_time parsing and flow through the system
</success_criteria>

<output>
After completion, create `.planning/quick/1-execute-pending-todos/1-SUMMARY.md`
</output>
