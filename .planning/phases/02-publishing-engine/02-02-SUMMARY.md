---
phase: 02-publishing-engine
plan: "02"
subsystem: publishing
tags: [mqtt, asyncio, worker-pool, concurrent, round-robin, structlog]

# Dependency graph
requires:
  - phase: 02-01
    provides: MQTTClient interface (connect, disconnect, publish, MQTTConnectionError, MQTTPublishError)
  - phase: 02-00
    provides: test infrastructure, pytest-asyncio, structlog
provides:
  - WorkerPool class managing N MQTTClient workers for concurrent publishing
  - WorkerConnectionError exception for fail-fast connection failure
  - Pre-connect all workers before publishing with fail-fast behavior
  - Concurrent publish dispatch using asyncio.gather with round-robin distribution
  - Graceful cleanup disconnecting all workers
affects:
  - 02-03-rate-limiter
  - 02-04-retry-policy
  - 02-05-publisher-orchestrator

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Pre-connect all workers sequentially before any publishing begins
    - Fail-fast on first connection error, disconnecting all already-connected workers
    - asyncio.gather with return_exceptions=True for fire-and-forget concurrent publish
    - Round-robin worker selection via counter modulo worker_count
    - Log individual publish failures without propagating (non-fatal per-message errors)

key-files:
  created:
    - src/loadgen/worker_pool.py
    - tests/test_worker_pool.py
  modified:
    - src/loadgen/__init__.py

key-decisions:
  - "asyncio.gather used instead of TaskGroup for Python 3.9 compatibility (TaskGroup requires 3.11+)"
  - "Individual publish failures logged but not raised — keeps other workers running"
  - "Placeholder MQTTClient in worker_pool.py for standalone testability (real MQTTClient wired in later)"

patterns-established:
  - "Worker pre-connect pattern: connect all before any publish, fail-fast with cleanup on error"
  - "Round-robin dispatch: _current_worker_index % worker_count, increment after each assignment"
  - "Non-fatal error logging: catch Exception in _worker_publish_task, log warning, return None"

requirements-completed: [PUB-03]

# Metrics
duration: 15min
completed: 2026-03-10
---

# Phase 2 Plan 02: Worker Pool Summary

**WorkerPool class with pre-connect fail-fast and asyncio.gather concurrent publish using round-robin distribution across N MQTT workers**

## Performance

- **Duration:** 15 min
- **Started:** 2026-03-09T23:40:00Z
- **Completed:** 2026-03-09T23:55:36Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- WorkerPool creates N MQTTClient workers from shared broker_config on initialization
- async initialize() pre-connects all workers sequentially with fail-fast cleanup on any failure
- async publish() dispatches messages concurrently with round-robin worker selection via asyncio.gather
- Individual publish failures are caught and logged (non-fatal) so other workers continue
- Cleanup method disconnects all connected workers and resets initialized state
- 13 tests across 4 test classes — all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Create WorkerPool with pre-connect logic (TDD RED)** - `15edebe` (test)
2. **Task 2: Implement concurrent publish dispatch (TDD GREEN)** - `695cb0f` (feat)
3. **Task 3: Export WorkerPool from package** - `dfd9e84` (feat)

_Note: TDD tasks have test commit followed by implementation commit._

## Files Created/Modified
- `src/loadgen/worker_pool.py` - WorkerPool class (280 lines): pre-connect, fail-fast, concurrent publish, round-robin, cleanup
- `tests/test_worker_pool.py` - 13 tests across TestWorkerPoolCreation, TestWorkerPoolInitialization, TestWorkerPoolCleanup, TestWorkerPoolPublish
- `src/loadgen/__init__.py` - Added WorkerPool, WorkerConnectionError exports and __all__ entries

## Decisions Made
- Used asyncio.gather with return_exceptions=True instead of asyncio.TaskGroup — TaskGroup requires Python 3.11+, project targets Python 3.9
- Individual publish failures are logged as warnings but not raised, allowing remaining workers to continue publishing
- Placeholder MQTTClient embedded in worker_pool.py for standalone unit testability; real MQTTClient from mqtt_client.py will be imported when wired up in publisher orchestrator

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- WorkerPool ready for integration with Rate Limiter (02-03) and Retry Policy (02-04)
- Publisher Orchestrator (02-05) will wire real MQTTClient import and integrate all components
- No blockers identified

## Self-Check

**Files exist:**
- FOUND: src/loadgen/worker_pool.py
- FOUND: tests/test_worker_pool.py
- FOUND: src/loadgen/__init__.py

**Commits verified:**
- 15edebe: test(02-02): add failing tests for concurrent publish dispatch
- 695cb0f: feat(02-02): implement concurrent publish dispatch with round-robin
- dfd9e84: feat(02-02): export WorkerPool from loadgen package

**Tests:** 13/13 passing

## Self-Check: PASSED

---
*Phase: 02-publishing-engine*
*Completed: 2026-03-10*
