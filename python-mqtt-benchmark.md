# Python MQTT Benchmark Plan (Separate Project)

## Context and decisions from discussion

This plan is based on the following production-realism considerations:

1. Periodic flow has overflow/dedup logic, so benchmark payloads must vary per message.
2. Load profile (LP) periodic has 96 slots/day per meter (15-minute windows).
3. For large simulations, meter identity must be realistic (many unique meters, not one meter repeated).
4. Initial validation should start smaller (`1k`, `5k`, `10k`) and verify linear scaling before larger runs.
5. Load generator should be a separate project from Mahabarata.
6. Resource monitoring (CPU and memory) is required on MacBook Pro M1 while benchmark runs.

Final implementation direction:
- Build a **separate Python load generator project** as the primary benchmark tool.
- Use `mqtt-benchmark` only as an optional broker baseline tool, not the main production-like simulation driver.

## Objective

Create a Python-based MQTT load generator that:
- reads real meter IDs from CSV,
- publishes realistic LP periodic events with unique keys,
- runs benchmark stages for `1,000`, `5,000`, and `10,000` events,
- captures throughput, publish success/failure, CPU, and memory,
- produces run artifacts and a linearity assessment to support extrapolation planning.

## Why custom Python instead of only mqtt-benchmark

`mqtt-benchmark` is useful for broker stress tests, but limited for this use case:
- difficult to guarantee per-message uniqueness (`trxId`, `samplingTime`),
- limited scenario semantics for periodic flow,
- harder to model production-like payload variance.

A custom Python publisher gives full control over:
- event identity,
- periodic slot logic,
- replay and observability,
- benchmark reproducibility.

## Scope (phase 1)

- Data type: **Load Profile** (`operationType = meterLoadProfilePeriodic`).
- Input: CSV with `meter_id` list.
- Run ladder:
  - 1,000 events
  - 5,000 events
  - 10,000 events
- One-shot LP event per meter in phase 1.
- Ensure no accidental duplicate suppression by generator design.
- Track process + host resource usage during runs.

Out of scope (phase 2+):
- full `96 slots/day/meter` scenario,
- mixed LP/Instantaneous/EOB scenario,
- distributed multi-machine load generation.

## Expected benchmark behavior against Werkudoro

For each event, keep uniqueness at least on:
- `trxId` (always unique)
- `(meterId, samplingTime)` pair (unique per run)

This aligns with periodic dedup behavior and avoids benchmark distortion from duplicate suppression.

## Project layout (separate repository)

```text
python-mqtt-loadgen/
  README.md
  pyproject.toml
  requirements.txt
  .env.example
  config/
    default.yaml
  scenarios/
    lp_1k.yaml
    lp_5k.yaml
    lp_10k.yaml
  src/
    main.py
    cli.py
    settings.py
    csv_loader.py
    payload_factory.py
    slot_planner.py
    publisher_async.py
    rate_limiter.py
    telemetry.py
    metrics.py
    reporter.py
  outputs/
    runs/
```

## Data and payload model

### CSV input
- Required column: `meter_id`
- Validation:
  - non-empty meter_id
  - deduplicate meter_id
  - report invalid rows

### Payload generation (LP)
Required envelope fields:
- `trxId`
- `meterId`
- `dcuId`
- `operationType = meterLoadProfilePeriodic`
- `operationResult` with LP fields

Field rules:
- `trxId`: UUID or deterministic sequence (`lp-{run_id}-{index}`)
- `samplingTime`: valid 15-minute boundary
- `collectionTime`: `samplingTime + delta`
- ensure `(meterId, samplingTime)` is unique in each run

## Publisher runtime design

Use async publisher (`asyncio`) with configurable:
- broker URI
- topic
- qos
- worker concurrency
- rate cap (msg/sec)
- ramp-up time
- retry policy (count + backoff)

Pipeline:
1. CSV reader stream
2. Payload factory
3. Async publish queue
4. Worker pool publish + retry
5. Metrics collector + telemetry sampler
6. Artifact writer

## Telemetry and metrics requirements

### Publish metrics
- planned event count
- sent count
- ack success count
- failed count
- retry count
- avg throughput (msg/sec)
- peak throughput (msg/sec)
- run duration

### Resource metrics (MacBook Pro M1)
- process CPU %
- process RSS memory
- system CPU %
- available system memory
- sampling interval: 1 second (configurable)

## Output artifacts per run

Create timestamped directory, e.g. `outputs/runs/2026-03-09T13-00-00-lp-1k/`:
- `run.json` (structured counters + timings + config snapshot)
- `telemetry.csv` (time-series CPU/memory)
- `summary.md` (human-readable run summary)
- `failed_events.jsonl` (replayable failed payloads)

## Benchmark execution ladder

Run in this order:

1. **Smoke test** (100 events)
   - validate payload format and topic wiring
2. **LP-1k**
3. **LP-5k**
4. **LP-10k**

Gate rules between stages:
- publish success ratio >= 99%
- no abnormal failure bursts
- resource usage remains stable (no memory runaway)
- throughput degradation is explainable

## Linearity analysis method

For runs `1k`, `5k`, `10k`, compare:
- total duration
- achieved msg/sec
- fail ratio
- avg/peak CPU
- avg/peak memory

Indicators:
- Duration should scale near linearly with event count.
- Msg/sec should not collapse as scale increases.
- Fail ratio should remain near-constant.
- CPU and memory should increase predictably (no cliff behavior).

Extrapolation policy:
- If scaling remains near-linear from `1k -> 5k -> 10k`, use this to estimate larger runs.
- If non-linear behavior appears, tune workers/rate and rerun ladder before extrapolating.

## Initial tuning baseline for M1

Starting config (safe baseline):
- workers: 50
- qos: 1
- rate cap: 1000 msg/sec
- ramp-up: 10s
- retry max: 3
- retry backoff: exponential, base 200ms
- telemetry interval: 1s

Adjustment guidance:
- If CPU < 60% and failures low, increase rate/workers.
- If CPU > 85% or failures rise, reduce rate/workers.

## Risks and mitigations

1. Duplicate suppression distorts benchmark
   - Mitigation: enforce unique `(meterId, samplingTime)` and unique `trxId`.

2. Publisher host bottleneck (local machine)
   - Mitigation: telemetry + capped rate + ramp-up.

3. Broker/downstream saturation causes non-linear behavior
   - Mitigation: staged ladder and gate rules.

4. CSV quality issues
   - Mitigation: pre-validation + invalid-row report.

## Implementation task list

1. Create separate Python project scaffold and dependency setup.
2. Implement CSV loader and validator (`meter_id` required).
3. Implement LP payload factory with uniqueness rules.
4. Implement async MQTT publisher with retry/backpressure control.
5. Implement telemetry sampler for CPU/memory.
6. Implement metrics aggregation and artifact writer.
7. Add scenario configs (`lp_1k`, `lp_5k`, `lp_10k`).
8. Execute smoke -> 1k -> 5k -> 10k benchmark ladder.
9. Generate linearity report and recommendation for next-scale test.

## Example CLI shape

```bash
python -m src.main run \
  --scenario scenarios/lp_1k.yaml \
  --csv /path/to/meter_ids.csv \
  --broker tcp://localhost:1883 \
  --topic meter-load-profile-periodic
```

```bash
python -m src.main compare \
  --runs outputs/runs/2026-03-09-lp-1k outputs/runs/2026-03-09-lp-5k outputs/runs/2026-03-09-lp-10k
```

## Success criteria

- Separate Python project ready and runnable.
- 1k, 5k, 10k runs complete with >=99% publish success.
- CPU/memory telemetry captured for all runs.
- Linearity summary generated from run artifacts.
- Clear recommendation whether to proceed to larger volume tests.
