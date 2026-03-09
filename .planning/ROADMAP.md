# Roadmap: Python MQTT Load Generator

**Milestone:** v1.0 Core
**Created:** 2026-03-09
**Granularity:** Coarse (3-5 phases)
**Status:** Executing

## Phases

- [x] **Phase 1: Input Foundation** - CSV meter ID loading with unique LP periodic payload generation
- [ ] **Phase 2: Publishing Engine** - Async MQTT client with configurable workers, rate limiting, and retry
- [ ] **Phase 3: Configuration & CLI** - Scenario configs, payload templates, and CLI run interface
- [ ] **Phase 4: Metrics & Artifacts** - Publish metrics tracking and structured run output

## Phase Details

### Phase 1: Input Foundation

**Goal:** Load real meter IDs from CSV and generate unique LP periodic payloads with guaranteed uniqueness constraints

**Depends on:** Nothing (first phase)

**Requirements:** INPUT-01, INPUT-02, INPUT-03, INPUT-04

**Success Criteria** (what must be TRUE):
1. User can load meter IDs from a CSV file with validation (file exists, readable format) and deduplication (duplicate IDs removed)
2. User can generate LP periodic payloads with unique `trxId` per message (UUID format)
3. User can generate unique `(meterId, samplingTime)` pairs per run (no duplicates within a single benchmark run)
4. User can assign valid 15-minute boundary timestamps via slot planner (timestamps align to :00, :15, :30, :45 minute boundaries)

**Plans:** 4/4 plans executed

- [x] 01-01-PLAN.md — Test infrastructure setup (pytest.ini, conftest.py, test stubs)
- [x] 01-02-PLAN.md — CSV meter ID loader with validation and deduplication
- [x] 01-03-PLAN.md — Slot planner for 15-minute boundary timestamps
- [x] 01-04-PLAN.md — Payload factory with uniqueness guarantees

---

### Phase 2: Publishing Engine

**Goal:** Publish generated payloads to MQTT broker asynchronously with configurable concurrency, rate control, and failure handling

**Depends on:** Phase 1 (requires payloads to publish)

**Requirements:** PUB-01, PUB-02, PUB-03, PUB-04, PUB-05

**Success Criteria** (what must be TRUE):
1. User can configure broker connection settings (host, port, TLS, username/password) via config
2. User can select QoS level (0, 1, or 2) and tool honors that setting for all publishes
3. User can configure worker count for concurrent publishing and tool publishes using that many async tasks
4. User can configure a message rate cap (msg/sec) and tool throttles publishing to not exceed that rate
5. Tool retries failed publishes with exponential backoff (configurable retry count and backoff multiplier)

**Plans:** 3/6 plans executed

- [x] 02-00-PLAN.md — Test infrastructure setup (test stubs for MQTT client, worker pool, rate limiter, retry policy)
- [x] 02-01-PLAN.md — MQTT client with connection config (TLS, auth) and QoS selection (PUB-01, PUB-02)
- [ ] 02-02-PLAN.md — Worker pool for concurrent publishing with pre-connect and fail-fast (PUB-03)
- [ ] 02-03-PLAN.md — Rate limiter with token bucket algorithm (PUB-04)
- [ ] 02-04-PLAN.md — Retry policy with exponential backoff (PUB-05)
- [ ] 02-05-PLAN.md — Publisher orchestrator with graceful shutdown

---

### Phase 3: Configuration & CLI

**Goal:** Provide scenario configurations and CLI interface for running benchmarks

**Depends on:** Phase 2 (requires publishing engine to execute scenarios)

**Requirements:** CONFIG-01, CONFIG-02, CONFIG-03, MEAS-03

**Success Criteria** (what must be TRUE):
1. User can configure scenarios for 1k, 5k, and 10k event runs via YAML files
2. User can configure MQTT topic for publishes (default: `meter/loadProfile`)
3. User can configure payload template structure (LP periodic envelope with configurable fields)
4. User can run benchmarks via CLI command `loadgen run --scenario scenario_1k.yaml`

**Plans:** TBD

---

### Phase 4: Metrics & Artifacts

**Goal:** Track publish outcomes and output structured run artifacts for analysis

**Depends on:** Phase 2 (requires publishing engine to measure), Phase 3 (requires CLI to trigger runs)

**Requirements:** MEAS-01, MEAS-02

**Success Criteria** (what must be TRUE):
1. Tool reports publish metrics after each run (sent count, acked count, failed count, throughput msg/sec, total duration)
2. Tool outputs run artifacts to a timestamped directory (run.json with full metadata, summary.md with human-readable results, failed_events.jsonl with failed payloads for replay)

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Input Foundation | 4/4 | Complete | 2026-03-09 |
| 2. Publishing Engine | 3/6 | In Progress|  |
| 3. Configuration & CLI | 0/4 | Not started | - |
| 4. Metrics & Artifacts | 0/2 | Not started | - |

## Dependencies

```
Phase 1 (Input Foundation)
    ↓
Phase 2 (Publishing Engine)
    ↓
Phase 3 (Configuration & CLI) ←→ Phase 4 (Metrics & Artifacts)
```

Phase 3 and Phase 4 can execute in parallel once Phase 2 is complete.

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| INPUT-01 | Phase 1 | Complete |
| INPUT-02 | Phase 1 | Complete |
| INPUT-03 | Phase 1 | Complete |
| INPUT-04 | Phase 1 | Complete |
| PUB-01 | Phase 2 | Complete |
| PUB-02 | Phase 2 | Complete |
| PUB-03 | Phase 2 | Pending |
| PUB-04 | Phase 2 | Pending |
| PUB-05 | Phase 2 | Pending |
| CONFIG-01 | Phase 3 | Pending |
| CONFIG-02 | Phase 3 | Pending |
| CONFIG-03 | Phase 3 | Pending |
| MEAS-01 | Phase 4 | Pending |
| MEAS-02 | Phase 4 | Pending |
| MEAS-03 | Phase 3 | Pending |

**Total:** 14 requirements mapped
**Coverage:** 100%

---
*Roadmap created: 2026-03-09*
*Last updated: 2026-03-09 (Plan 02-01 complete)*
