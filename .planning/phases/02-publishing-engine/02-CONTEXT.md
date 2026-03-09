# Phase 2: Publishing Engine - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

## Phase Boundary

Publish generated payloads to MQTT broker asynchronously with configurable concurrency, rate control, and failure handling. This phase builds PUB-01 through PUB-05: broker connection configuration, QoS selection, async workers, rate limiting, and retry with exponential backoff.

## Implementation Decisions

### Worker Connections
- **Pre-connect all workers** at startup before publishing begins (slower startup, no connection latency during messages)
- **Fail-fast** if any worker fails to connect during startup (abort entire run, no partial work)
- **Default MQTT keepalive** (60 seconds) — use aiomqtt's built-in keepalive
- **Fresh connections per benchmark run** — each run (1k, 5k, 10k) establishes new connections for clean isolation

### Rate Limiting Scope
- **Global shared rate cap** across all workers (e.g., 1000 msg/sec total, simpler to reason about target throughput)
- **Token bucket algorithm** — allows bursts within capacity while maintaining long-term rate
- **Block/wait** when rate exceeded (simple backpressure, messages never dropped)
- **Second-level precision** for rate tracking (sufficient for benchmarks, simpler implementation)

### Retry Policy
- **Only QoS failures are retryable** — PUBACK timeout and MQTT-level QoS 1 acknowledgment failures. Connection errors and broker errors are NOT retried.
- **Configurable max retries** via YAML scenario config (e.g., `retry: 3`)
- **Configurable backoff strategy** via YAML — both strategy type (exponential, fixed, linear) and multiplier
- **Skip to artifact** on exhausted retries — failed messages written to `failed_events.jsonl` for replay analysis, run continues

### Graceful Shutdown
- **Immediate abort** on Ctrl+C — stop publishing immediately, do not drain queue or finish pending work
- **Partial artifacts** on interruption — write `run.json` with partial results for debugging
- **Graceful MQTT DISCONNECT** before closing connections — send DISCONNECT packet (polite cleanup)
- **Force quit** on double Ctrl+C — emergency exit, skip all cleanup

### Claude's Discretion
- Exact token bucket capacity and refill rate implementation
- Connection retry/backoff if pre-connect phase fails (before fail-fast)
- Shutdown timeout for graceful DISCONNECT (how long to wait before force close)

## Specific Ideas

- Immediate abort + graceful DISCONNECT combo: stop work fast but close connections politely
- QoS-only retry scope keeps retry logic focused on MQTT protocol semantics, not network issues

## Existing Code Insights

### Reusable Assets
- `src/loadgen/payload.py` — PayloadFactory generates LP periodic payloads with unique (meterId, samplingTime) pairs
- `src/loadgen/csv_reader.py` — Meter ID loading from CSV (provides input for publishing)
- `src/loadgen/slot_planner.py` — 15-minute boundary timestamp generation

### Established Patterns
- Pytest test infrastructure with `pytest.ini` and `conftest.py`
- Structured logging with structlog (from STACK.md research)
- Test-driven development approach from Phase 1

### Integration Points
- Publishing engine will consume payloads from PayloadFactory
- Meter IDs from CSV reader provide the publish targets
- Rate limiting config comes from YAML scenario files (Phase 3)

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 02-publishing-engine*
*Context gathered: 2026-03-10*
