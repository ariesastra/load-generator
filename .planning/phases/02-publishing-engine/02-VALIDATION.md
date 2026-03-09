---
phase: 02
slug: publishing-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-10
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini (exists from Phase 1) |
| **Quick run command** | `pytest tests/ -v -k "test_" --tb=short` |
| **Full suite command** | `pytest tests/ -v --cov=src/loadgen --cov-report=term-missing` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v -k "test_" --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --cov=src/loadgen --cov-report=term-missing`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | PUB-01 | unit | `pytest tests/test_mqtt_client.py -v` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | PUB-02 | unit | `pytest tests/test_mqtt_client.py -v` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | PUB-03 | unit | `pytest tests/test_worker_pool.py -v` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 2 | PUB-04 | unit | `pytest tests/test_rate_limiter.py -v` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | PUB-05 | unit | `pytest tests/test_retry_policy.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_mqtt_client.py` — stubs for PUB-01, PUB-02 (MQTT client connection, QoS configuration)
- [ ] `tests/test_worker_pool.py` — stubs for PUB-03 (worker pool for concurrent publishing)
- [ ] `tests/test_rate_limiter.py` — stubs for PUB-04 (rate limiter for publish throttling)
- [ ] `tests/test_retry_policy.py` — stubs for PUB-05 (retry with exponential backoff)
- [ ] `tests/conftest.py` — shared fixtures (exists from Phase 1, may need extension)

*Framework exists from Phase 1. New test stubs needed for publishing engine components.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Actual MQTT broker connection | PUB-01 | Requires external broker | Connect to test broker (e.g., mosquitto) and verify connection |
| QoS level honor on publish | PUB-02 | Requires broker QoS support | Publish at each QoS level, verify broker receives accordingly |
| Concurrent publish behavior | PUB-03 | Requires observable concurrency | Monitor active connections during publish |
| Rate limiting accuracy | PUB-04 | Requires timing validation | Publish with rate cap, verify not exceeded |
| Retry backoff behavior | PUB-05 | Requires time-based validation | Trigger failure, observe retry delays |

*Integration behaviors require external MQTT broker. Unit tests use mocks.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
