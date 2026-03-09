# Python MQTT Load Generator

## What This Is

A standalone Python-based MQTT load generator that publishes realistic Load Profile periodic events to benchmark Werkudoro's data-collection service. It reads real meter IDs from CSV, generates unique payloads with proper `trxId` and `samplingTime` values, and runs a scaling ladder (1k → 5k → 10k) to prove linear throughput before committing to the 200k production target.

## Core Value

Prove that Werkudoro's data-collection can handle production-scale MQTT traffic (200k events) by demonstrating linear scaling characteristics with realistic, non-duplicate payloads.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Read meter IDs from real CSV input
- [ ] Generate LP periodic payloads with unique trxId and (meterId, samplingTime) per run
- [ ] Async MQTT publisher with configurable workers, rate cap, QoS, and retry
- [ ] Resource telemetry (CPU/memory) during benchmark runs
- [ ] Publish metrics (sent, acked, failed, throughput, duration)
- [ ] Scenario configs for 1k, 5k, 10k event runs
- [ ] Run artifact output (run.json, telemetry.csv, summary.md, failed_events.jsonl)
- [ ] Linearity analysis comparing runs across the scaling ladder
- [ ] CLI interface for running scenarios and comparing results

### Out of Scope

- Full 96 slots/day/meter scenario — phase 2+, adds complexity without validating core scaling
- Mixed LP/Instantaneous/EOB scenario — phase 2+, one data type sufficient to prove scaling
- Distributed multi-machine load generation — single M1 MacBook sufficient for 200k target validation
- GUI or web dashboard — CLI artifacts are sufficient for analysis
- Broker deployment/management — broker runs separately in local Docker

## Context

- **Target system:** Werkudoro data-collection service (part of Mahabarata/Aegis ecosystem)
- **Benchmark environment:** MacBook Pro M1, broker in local Docker
- **Production target:** 200k events — this tool proves the path there
- **Data type:** `operationType = meterLoadProfilePeriodic` with realistic envelope fields
- **Existing tools gap:** `mqtt-benchmark` cannot guarantee per-message uniqueness or model periodic flow semantics, leading to benchmark distortion from duplicate suppression
- **Payload uniqueness is critical:** Werkudoro's periodic flow has overflow/dedup logic — duplicate `(meterId, samplingTime)` pairs get suppressed, distorting results

## Constraints

- **Tech stack**: Python with asyncio — matches team expertise and provides full payload control
- **Timeline**: This week — need benchmark results to validate production readiness
- **Environment**: Single MacBook Pro M1 — both generator and Docker broker run locally
- **Data source**: Real meter IDs from existing CSV — no synthetic generation needed
- **Broker protocol**: MQTT with QoS 1 — matches production configuration

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Separate project from Mahabarata | Clean separation of concerns; reusable benchmarking tool | — Pending |
| Python + asyncio over Go/Rust | Team familiarity; full control over payload generation; sufficient performance for 200k | — Pending |
| Scaling ladder (1k→5k→10k) before 200k | Validate linear scaling cheaply before committing to full production volume | — Pending |
| Real CSV over synthetic meter IDs | Production-realistic benchmark; real data already available | — Pending |

---
*Last updated: 2026-03-09 after initialization*
