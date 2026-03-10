---
phase: 03-configuration-cli
plan: 01
subsystem: Configuration
tags: [config, yaml, validation, dataclasses]
dependency_graph:
  requires:
    - "Phase 1: Input Foundation (PayloadFactory, SlotPlanner, CSV loader)"
    - "Phase 2: Publishing Engine (Publisher orchestrator interface)"
  provides:
    - "YAML configuration schema for scenarios"
    - "load_config() function for CLI consumption"
    - "Config validation with clear error messages"
  affects:
    - "Phase 3-02: CLI will use load_config() to parse user scenarios"
    - "Phase 3-03: Artifact writer will use config for output paths"
tech_stack:
  added:
    - "PyYAML 6.0.3: YAML parsing"
  patterns:
    - "dataclasses: Type-safe configuration with __post_init__ validation"
    - "Union[str, Path]: Python 3.9 compatible type annotations"
    - "ConfigValidationError: Clear, actionable error messages"
key_files:
  created:
    - path: "src/loadgen/config.py"
      lines: 337
      exports: ["ScenarioConfig", "BrokerConfig", "MqttConfig", "PayloadConfig", "load_config", "ConfigValidationError"]
    - path: "tests/test_config.py"
      tests: 20
      coverage: "validation, defaults, type conversion, file errors"
  modified:
    - path: "src/loadgen/__init__.py"
      changes: "Added config exports and missing Phase 1 exports (PayloadFactory, SlotPlanner)"
decisions: []
metrics:
  duration: "5 minutes"
  completed_date: "2026-03-11T00:28:00Z"
  tasks_completed: 4
  files_created: 2
  tests_added: 20
  lines_of_code: 724
---

# Phase 03 Plan 01: Configuration Schema and YAML Loader Summary

## One-Liner
YAML-based configuration system using Python dataclasses with validation, enabling users to define broker settings, MQTT topics, payload templates, and scenario parameters without code changes.

## Implementation Summary

Created a comprehensive configuration system for MQTT load generator scenarios using Python stdlib dataclasses and PyYAML. The system provides type-safe configuration with validation and clear error messages for all failure modes.

### Tasks Completed

1. **Configuration Data Classes** (Task 1)
   - Created `BrokerConfig` with host, port, TLS, and auth credentials
   - Created `MqttConfig` with topic and QoS validation (0/1/2 only)
   - Created `PayloadConfig` with DCU ID and meter ID source
   - Created `ScenarioConfig` with full scenario parameters
   - Created `ConfigValidationError` exception for validation failures
   - Implemented `__post_init__` validation for all dataclasses
   - Auto-set TLS port to 8883 when using default port with TLS enabled

2. **YAML Loader with Validation** (Task 2)
   - Implemented `load_config()` function with Union[str, Path] support
   - Validates file existence with clear FileNotFoundError
   - Validates YAML syntax with descriptive error messages
   - Maps nested dicts to dataclass instances (broker, mqtt, payload)
   - Validates required fields (name, message_count, rate_limit)
   - Validates QoS is 0, 1, or 2
   - Validates positive integers for counts and rate limits
   - Validates meter_id_source file exists if provided
   - Provides actionable error messages for all validation failures

3. **Comprehensive Test Suite** (Task 3)
   - Created 20 tests covering all validation scenarios
   - Tests for valid configuration loading with all fields
   - Tests for minimal configuration with default values
   - Tests for missing required fields (name, message_count, rate_limit)
   - Tests for invalid QoS values (3, -1, etc.)
   - Tests for negative/invalid integer values
   - Tests for non-existent meter_id_source files
   - Tests for invalid YAML syntax
   - Tests for type conversion (YAML strings to ints)
   - Tests for TLS auto-port configuration
   - Tests for file not found and empty config files
   - All 20 tests passing with 100% success rate

4. **Package Exports** (Task 4)
   - Added config module imports to `loadgen/__init__.py`
   - Exported all config classes (ScenarioConfig, BrokerConfig, MqttConfig, PayloadConfig)
   - Exported load_config() function
   - Exported ConfigValidationError exception
   - Fixed missing Phase 1 exports (PayloadFactory, SlotPlanner)
   - All exports accessible from loadgen package for CLI consumption

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Added PyYAML dependency**
- **Found during:** Task 1 verification
- **Issue:** PyYAML package was not installed, causing import error
- **Fix:** Installed PyYAML 6.0.3 using pip3
- **Files modified:** None (dependency installation only)
- **Commit:** N/A (dependency installation)

**2. [Rule 1 - Bug] Fixed case sensitivity in test assertion**
- **Found during:** Task 3 test execution
- **Issue:** Test assertion checked for "Invalid" (capital I) but error message was "invalid" (lowercase)
- **Fix:** Changed assertion to use `.lower()` for case-insensitive matching
- **Files modified:** `tests/test_config.py`
- **Commit:** f0d4be3 (test commit with fix included)

**3. [Rule 3 - Auto-fix Blocking Issue] Set PYTHONPATH for imports**
- **Found during:** Task 1 verification
- **Issue:** Python couldn't import loadgen module without PYTHONPATH set
- **Fix:** Used PYTHONPATH=/Users/ariesastra/Code/Works/aegis/python-loadgen/src for all test commands
- **Files modified:** None (test execution only)
- **Commit:** N/A (test execution environment)

## Key Technical Decisions

### Dataclasses over Pydantic
Chose Python stdlib dataclasses over Pydantic for configuration schema:
- **Rationale:** Keep dependencies minimal, use stdlib where possible
- **Trade-off:** Manual validation in `__post_init__` vs. automatic validation
- **Outcome:** Type-safe configuration with custom validation logic

### Union[str, Path] for Python 3.9 Compatibility
Used `Union[str, Path]` instead of pipe syntax (`str | Path`) in type annotations:
- **Rationale:** Project targets Python 3.9, pipe syntax requires 3.10+
- **Impact:** All type annotations compatible with Python 3.9

### Auto-set TLS Port to 8883
Implemented automatic TLS port switching:
- **Behavior:** When `tls=true` and port is default (1883), auto-set to 8883
- **Rationale:** Sensible default for TLS connections, allows custom ports
- **Edge Case:** Explicit port values are respected (e.g., port 9000 with TLS)

## Integration Points

### Publisher Interface Mapping
YAML configuration maps to Publisher parameters:
- `broker_config` (host, port, tls, username, password) → `Publisher.broker_config`
- `scenario.message_count` → `Publisher.message_count`
- `scenario.worker_count` → `Publisher.worker_count`
- `scenario.rate_limit` → `Publisher.rate_limit`
- `scenario.qos` → `Publisher.qos`
- `payload.dcu_id` → `Publisher.dcu_id` (via PayloadFactory)
- `mqtt.topic` → Not used in Publisher yet (will be added in 03-02)

### CLI Consumption (Phase 3-02)
The `load_config()` function will be used by the CLI module:
- CLI accepts `--config` parameter pointing to YAML file
- CLI calls `load_config()` to load and validate scenario
- CLI passes `ScenarioConfig` to Publisher orchestrator

## Test Coverage

### 20 Tests Covering:
- Valid configuration loading with all fields
- Minimal configuration with default values
- Missing required fields (3 tests)
- Invalid QoS values (2 tests)
- Negative/invalid integer values (3 tests)
- Non-existent meter_id_source file
- Invalid YAML syntax
- Invalid broker section
- Invalid port type
- Empty broker host
- Type conversion (strings to ints)
- Boolean conversion
- TLS auto-port configuration
- File not found
- Empty config file

### Test Results:
```
============================== 20 passed in 0.11s ==============================
```

## Files Created/Modified

### Created:
1. `src/loadgen/config.py` (337 lines)
   - Configuration data classes
   - YAML loader with validation
   - ConfigValidationError exception

2. `tests/test_config.py` (387 lines)
   - 20 comprehensive tests
   - 100% pass rate

### Modified:
1. `src/loadgen/__init__.py` (+18 lines, -6 lines)
   - Added config module exports
   - Added missing Phase 1 exports (PayloadFactory, SlotPlanner)

## Dependencies Added

- **PyYAML 6.0.3**: YAML parsing and safe loading

## Next Steps

### Phase 3-02: CLI Module
- Use `load_config()` to parse user-provided YAML files
- Create CLI entry point with `--config` parameter
- Integrate with Publisher orchestrator

### Phase 3-03: Artifact Writer
- Use config for output directory paths
- Write run artifacts based on scenario configuration

## Verification

### Success Criteria Met:
- [x] User can load scenario configuration from YAML file with `load_config()`
- [x] Configuration includes all required fields (broker, mqtt, payload, scenario)
- [x] Invalid configurations are rejected with clear, actionable error messages
- [x] Config classes exported from loadgen package for use in CLI
- [x] Missing Phase 1 exports (PayloadFactory, SlotPlanner) now available
- [x] All 20 tests passing with comprehensive validation coverage
- [x] Python 3.9 compatible type annotations

### Manual Verification:
```bash
# Load a valid configuration
PYTHONPATH=src python3 -c "
from loadgen import load_config
config = load_config('examples/scenario.yaml')
print(f'Loaded: {config.name} ({config.message_count} messages)')
"

# Verify validation works
PYTHONPATH=src python3 -c "
from loadgen import load_config, ConfigValidationError
try:
    config = load_config('invalid.yaml')
except ConfigValidationError as e:
    print(f'Validation error: {e}')
"
```

## Self-Check: PASSED

All created files exist:
- [x] src/loadgen/config.py (337 lines)
- [x] tests/test_config.py (387 lines)
- [x] src/loadgen/__init__.py (modified)

All commits exist:
- [x] c3ff2ff: feat(03-01): create configuration data classes
- [x] ac06397: feat(03-01): implement YAML loader with validation
- [x] f0d4be3: test(03-01): create comprehensive config loading tests
- [x] 53bf67d: feat(03-01): export config module and missing Phase 1 exports

All tests pass:
- [x] 20/20 tests passing (100%)

Plan execution complete successfully.
