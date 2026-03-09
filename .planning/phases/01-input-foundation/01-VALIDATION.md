---
phase: 1
slug: input-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pytest.ini (Wave 0 installs) |
| **Quick run command** | `pytest tests/ -v -k "test_"` |
| **Full suite command** | `pytest tests/ -v --cov=src` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -v -k "test_" --tb=short`
- **After every plan wave:** Run `pytest tests/ -v --cov=src`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INPUT-01 | unit | `pytest tests/test_csv_loader.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INPUT-01 | unit | `pytest tests/test_csv_loader.py -k "validate"` | ❌ W0 | ⬜ pending |
| 01-02-01 | 01 | 2 | INPUT-02 | unit | `pytest tests/test_payload_factory.py` | ❌ W0 | ⬜ pending |
| 01-03-01 | 02 | 1 | INPUT-03 | unit | `pytest tests/test_uniqueness.py` | ❌ W0 | ⬜ pending |
| 01-04-01 | 03 | 1 | INPUT-04 | unit | `pytest tests/test_slot_planner.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_csv_loader.py` — stubs for INPUT-01 CSV loading validation
- [ ] `tests/test_payload_factory.py` — stubs for INPUT-02 payload generation
- [ ] `tests/test_uniqueness.py` — stubs for INPUT-03 uniqueness tracking
- [ ] `tests/test_slot_planner.py` — stubs for INPUT-04 slot planning
- [ ] `tests/conftest.py` — shared fixtures (sample CSV, test meter IDs)
- [ ] `pytest.ini` — pytest configuration

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CSV file format readability | INPUT-01 | Needs file system | Verify Asset-Meter.csv loads without error, logs duplicate count |
| Payload JSON schema validity | INPUT-02 | Visual inspection | Generate sample payload, verify against python-mqtt-benchmark.md spec |
| 15-minute boundary alignment | INPUT-04 | Time validation | Verify generated timestamps end in :00, :15, :30, :45 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
