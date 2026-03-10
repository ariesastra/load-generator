# Requirements: Python MQTT Load Generator

**Defined:** 2026-03-09
**Core Value:** Prove that Werkudoro's data-collection can handle production-scale MQTT traffic (200k events) by demonstrating linear scaling characteristics with realistic, non-duplicate payloads.

## v1 Requirements

Requirements for v1.0 Core milestone. Each maps to roadmap phases.

### Input & Data

- [x] **INPUT-01**: Tool can load meter IDs from CSV file with validation and deduplication
- [x] **INPUT-02**: Tool can generate LP periodic payloads with unique `trxId` per message
- [x] **INPUT-03**: Tool can generate unique `(meterId, samplingTime)` pairs per run
- [x] **INPUT-04**: Tool can assign valid 15-minute boundary timestamps via slot planner

### Publishing

- [x] **PUB-01**: User can configure broker connection (host, port, TLS, auth)
- [x] **PUB-02**: User can select QoS level (0, 1, or 2)
- [x] **PUB-03**: Tool can publish asynchronously with configurable worker count
- [x] **PUB-04**: Tool can rate-limit messages (msg/sec cap)
- [ ] **PUB-05**: Tool can retry failed publishes with exponential backoff

### Measurement & Output

- [ ] **MEAS-01**: Tool can report publish metrics (sent, acked, failed, throughput, duration)
- [ ] **MEAS-02**: Tool can output run artifacts (run.json, summary.md, failed_events.jsonl)
- [ ] **MEAS-03**: Tool can be run via CLI `run` command

### Configuration

- [ ] **CONFIG-01**: User can configure scenario for 1k, 5k, 10k event runs
- [x] **CONFIG-02**: User can configure MQTT topic
- [x] **CONFIG-03**: User can configure payload template

## v2 Requirements

Deferred to v1.1 milestone. Not in current roadmap.

### Telemetry & Analysis

- **TELEM-01**: Tool can capture host resource telemetry (CPU/memory) during runs
- **TELEM-02**: Tool can output telemetry.csv with time-series data
- **TELEM-03**: Tool can analyze linearity across scaling ladder runs
- **TELEM-04**: Tool can compare runs via CLI `compare` command

### Ladder Automation

- **LADDER-01**: Tool can execute automated scaling ladder with gate rules
- **LADDER-02**: Tool can enforce pass/fail gates between ladder stages

### Differentiators

- **DIFF-01**: Tool can enforce per-message uniqueness guarantees
- **DIFF-02**: Tool can generate domain-aware LP periodic envelope payloads
- **DIFF-03**: Tool can use real meter IDs from CSV (production-realistic)
- **DIFF-04**: Tool can ramp up publish rate gradually (avoid thundering herd)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Full 96 slots/day/meter scenario | Phase 2+; adds complexity without validating core scaling |
| Mixed LP/Instantaneous/EOB scenarios | Phase 2+; one data type sufficient to prove scaling |
| Distributed multi-machine load generation | Single M1 MacBook sufficient for 200k target validation |
| GUI or web dashboard | CLI artifacts are sufficient for analysis |
| Broker deployment/management | Broker runs separately in local Docker |
| Subscriber-side latency measurement | Focus is throughput validation, not latency profiling |
| MQTT 5.0 and WebSocket support | Production uses MQTT 3.1.1 over TCP; premature generalization |
| Plugin/extension system | Python modules and YAML configs provide sufficient extensibility |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INPUT-01 | Phase 1 | Complete |
| INPUT-02 | Phase 1 | Complete |
| INPUT-03 | Phase 1 | Complete |
| INPUT-04 | Phase 1 | Complete |
| PUB-01 | Phase 2 | Complete |
| PUB-02 | Phase 2 | Complete |
| PUB-03 | Phase 2 | Complete |
| PUB-04 | Phase 2 | Complete |
| PUB-05 | Phase 2 | Pending |
| CONFIG-01 | Phase 3 | Pending |
| CONFIG-02 | Phase 3 | Pending |
| CONFIG-03 | Phase 3 | Pending |
| MEAS-01 | Phase 4 | Pending |
| MEAS-02 | Phase 4 | Pending |
| MEAS-03 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14 (100%)
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-09*
*Last updated: 2026-03-09 after roadmap creation*
