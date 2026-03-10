# Feature Research

**Domain:** MQTT Load Generation / Benchmark Tooling
**Researched:** 2026-03-09
**Confidence:** MEDIUM (web search unavailable; based on training data knowledge of emqtt-bench, mqtt-benchmark, mqttloader, Gatling/JMeter MQTT plugins, mqtt-stresser, and project-specific requirements from benchmark plan)

## Feature Landscape

### Table Stakes (Users Expect These)

Features any MQTT load generator must have. Missing these means the tool is not credible for benchmarking.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Configurable broker connection (host, port, TLS, auth) | Every MQTT tool supports this; without it you cannot connect | LOW | Support `tcp://` and `ssl://` URI schemes, username/password, client certificate |
| QoS level selection (0, 1, 2) | MQTT fundamental; QoS 1 is the production target here | LOW | QoS 1 required for production parity; QoS 0 useful for max-throughput baseline |
| Configurable topic | Basic MQTT publishing requires a topic | LOW | Single topic sufficient for phase 1 |
| Configurable concurrency (worker count) | All load generators let you control parallelism | LOW | asyncio task pool; start at 50 workers per benchmark plan |
| Rate limiting (msg/sec cap) | Without rate control, you cannot produce repeatable results or protect the broker | MEDIUM | Token bucket or sliding window; critical for controlled scaling ladder |
| Publish result tracking (sent/acked/failed counts) | Core purpose of a benchmark tool is measuring success | MEDIUM | Track per-message outcomes with PUBACK correlation for QoS 1 |
| Run duration and throughput reporting | Users need to know msg/sec achieved and total time | LOW | Compute from publish timestamps |
| Failed message capture | Need to know what failed for debugging | LOW | JSONL output of failed payloads for replay |
| CLI interface | Standard UX for benchmark tools; no one expects a GUI | LOW | argparse or click; `run` and `compare` subcommands |
| Configurable payload (at minimum: static or template) | Every load generator lets you define what gets published | MEDIUM | Template-based generation with per-message field variation |

### Differentiators (Competitive Advantage)

Features that set this tool apart from generic MQTT load generators. These directly address the project's core value: realistic, non-duplicate payload simulation for dedup-sensitive systems.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Per-message payload uniqueness guarantees | Core differentiator. Generic tools (emqtt-bench, mqtt-benchmark) publish identical or random payloads -- they cannot guarantee unique `(meterId, samplingTime)` pairs. Werkudoro's periodic flow suppresses duplicates, making generic benchmarks meaningless. | MEDIUM | Payload factory must enforce uniqueness constraints at generation time, not hope for randomness |
| Domain-aware payload factory (LP periodic envelope) | Payloads match production schema: `trxId`, `meterId`, `dcuId`, `operationType`, `operationResult` with LP fields. No other off-the-shelf tool models Werkudoro's envelope format. | MEDIUM | Typed payload builder with field-level rules (UUID trxId, 15-min boundary samplingTime, etc.) |
| Real data input (CSV meter IDs) | Uses production meter identifiers instead of synthetic data. Makes benchmark results directly comparable to production behavior. | LOW | CSV loader with validation, dedup, invalid-row reporting |
| Slot planner (samplingTime assignment) | Assigns valid 15-minute boundary timestamps ensuring no `(meterId, samplingTime)` collision within a run. Generic tools have no concept of time-slot semantics. | MEDIUM | Cartesian product of meters x time slots, truncated to target event count |
| Scaling ladder with gate rules | Automated progression through 1k/5k/10k with pass/fail gates (>=99% success, stable resources, no failure bursts). Most tools just run once at a fixed load. | MEDIUM | Gate evaluation between stages; abort on failure |
| Host resource telemetry (CPU/memory time series) | Captures generator-side resource usage during runs. Distinguishes "broker slow" from "generator bottlenecked." emqtt-bench and mqtt-benchmark do not capture this. | MEDIUM | psutil sampling at 1s intervals; output to telemetry.csv |
| Linearity analysis across runs | Compares throughput, duration, fail ratio, and resource usage across the scaling ladder. Answers "will this scale to 200k?" No off-the-shelf tool does this. | MEDIUM | Statistical comparison of run artifacts; linear regression on msg/sec vs event count |
| Structured run artifacts | Timestamped output directory with `run.json`, `telemetry.csv`, `summary.md`, `failed_events.jsonl`. Makes runs reproducible and comparable. | LOW | Artifact writer module; one directory per run |
| Deterministic/reproducible runs | Given same CSV + scenario config, produces the same payload sequence (modulo timestamps). Enables re-running to verify fixes. | LOW | Deterministic trxId generation (`lp-{run_id}-{index}`) rather than random UUIDs |
| Ramp-up period | Gradually increases publish rate to avoid thundering-herd broker overload at start. Some tools have this (Gatling), most simple ones do not. | LOW | Linear ramp from 0 to target rate over configurable duration |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| GUI / web dashboard | "Visualize results in real-time" | Massive scope increase for a CLI benchmark tool. Time-series CSV + summary.md are sufficient for the scaling validation goal. Building a dashboard delays the actual benchmarking work. | Generate `summary.md` with key metrics; import `telemetry.csv` into Grafana or a notebook if visualization is needed |
| Subscriber-side latency measurement | "Measure end-to-end latency" | Requires a companion subscriber process, clock sync, and coordination logic. Doubles complexity. The goal here is throughput validation, not latency profiling. | Measure publish-to-PUBACK latency (publisher-side only) as a proxy; defer true e2e latency to a separate tool or phase 2 |
| Distributed multi-machine load generation | "Scale beyond single machine" | Adds orchestration, result aggregation, clock sync, and deployment complexity. Single M1 MacBook is sufficient for the 200k target. | Validate single-machine ceiling first; only distribute if M1 proves insufficient |
| Mixed protocol support (MQTT 3.1.1 + 5.0 + WebSocket) | "Future-proof the tool" | Premature generalization. Production uses MQTT 3.1.1 over TCP. Supporting MQTT 5.0 and WebSocket adds testing surface without validation value. | Hardcode MQTT 3.1.1/TCP for now; abstract the client interface so v5 can be added later if needed |
| Mixed message type scenarios (LP + Instantaneous + EOB) | "Test all data types at once" | Increases payload factory complexity 3x. One data type is sufficient to prove scaling characteristics. Mixed scenarios add variables that make linearity analysis harder to interpret. | Validate LP periodic first; add Instantaneous and EOB as separate scenario types in phase 2 |
| Dynamic meter ID generation (synthetic) | "Don't depend on CSV files" | Defeats the purpose of production-realistic benchmarking. Synthetic IDs may not match production ID patterns or cardinality. | Always use real CSV input; provide a sample CSV for quick-start |
| Automatic broker provisioning | "One-click setup including broker" | Tight coupling to Docker/infrastructure. Broker is an external dependency that should be managed separately. | Document broker setup in README; provide a `docker-compose.yml` as convenience, not as part of the tool |
| Plugin/extension system | "Make it extensible for future payload types" | Over-engineering for a focused tool. Python modules and YAML configs provide sufficient extensibility without a plugin framework. | Use Python module structure; new payload types = new factory class |

## Feature Dependencies

```
[CSV Loader]
    |
    v
[Payload Factory (LP Periodic)]
    |              |
    v              v
[Slot Planner]  [Unique trxId Generation]
    |              |
    +------+-------+
           |
           v
[Async MQTT Publisher]
    |              |
    v              v
[Rate Limiter]  [Retry Logic]
    |              |
    +------+-------+
           |
           v
[Metrics Collector]
    |              |
    v              v
[Telemetry Sampler]  [Artifact Writer]
    |                    |
    +--------+-----------+
             |
             v
[Scenario Runner (ladder + gates)]
             |
             v
[Linearity Analyzer / Compare CLI]
```

### Dependency Notes

- **Payload Factory requires CSV Loader:** Must have meter IDs before generating payloads
- **Slot Planner requires CSV Loader:** Needs meter ID count to plan time slots without collision
- **Publisher requires Payload Factory:** Publishes generated payloads
- **Metrics Collector requires Publisher:** Collects outcomes from publish operations
- **Scenario Runner requires all core components:** Orchestrates the full pipeline
- **Linearity Analyzer requires Artifact Writer:** Compares structured run outputs across multiple runs
- **Telemetry Sampler is independent:** Runs as a background task alongside the publisher; no dependency on payload generation

## MVP Definition

### Launch With (v1)

Minimum viable: run the scaling ladder and get a linearity answer.

- [ ] CSV loader with validation and dedup -- foundation for realistic payloads
- [ ] LP periodic payload factory with unique `trxId` and `(meterId, samplingTime)` guarantees -- the core differentiator
- [ ] Slot planner for 15-minute boundary timestamp assignment -- ensures uniqueness semantics
- [ ] Async MQTT publisher with configurable workers, QoS 1, and rate cap -- the execution engine
- [ ] Basic retry logic (count + exponential backoff) -- handles transient failures
- [ ] Publish metrics (sent/acked/failed/throughput/duration) -- answers "did it work?"
- [ ] Run artifact output (run.json, summary.md, failed_events.jsonl) -- makes runs inspectable
- [ ] Scenario configs for 1k, 5k, 10k -- defines the scaling ladder
- [ ] CLI `run` command -- executes a single scenario

### Add After Validation (v1.x)

Features to add once the core scaling ladder works.

- [ ] Host resource telemetry (CPU/memory sampling) -- add when needing to diagnose generator bottlenecks
- [ ] Telemetry.csv output -- pairs with resource telemetry
- [ ] Gate rules between ladder stages -- add when automating the full ladder sequence
- [ ] CLI `compare` command with linearity analysis -- add when multiple run artifacts exist
- [ ] Ramp-up period -- add if thundering-herd effects appear in initial runs
- [ ] Deterministic run IDs for reproducibility -- add when re-run comparison matters

### Future Consideration (v2+)

- [ ] Full 96 slots/day/meter scenario -- deferred because it adds complexity without changing the scaling answer
- [ ] Mixed LP/Instantaneous/EOB scenarios -- deferred until LP scaling is proven
- [ ] MQTT 5.0 support -- deferred until production moves to v5
- [ ] Publish-to-PUBACK latency percentiles (p50/p95/p99) -- useful but not needed for throughput validation
- [ ] Configuration profiles for different broker environments (cloud, on-prem) -- deferred until tool is used beyond local Docker

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| CSV loader + validation | HIGH | LOW | P1 |
| LP payload factory + uniqueness | HIGH | MEDIUM | P1 |
| Slot planner | HIGH | MEDIUM | P1 |
| Async MQTT publisher | HIGH | MEDIUM | P1 |
| Rate limiter | HIGH | LOW | P1 |
| Retry logic | MEDIUM | LOW | P1 |
| Publish metrics | HIGH | LOW | P1 |
| Run artifacts (run.json, summary.md) | HIGH | LOW | P1 |
| Scenario configs (YAML) | MEDIUM | LOW | P1 |
| CLI run command | HIGH | LOW | P1 |
| Failed events JSONL | MEDIUM | LOW | P1 |
| Resource telemetry | MEDIUM | MEDIUM | P2 |
| Telemetry CSV output | MEDIUM | LOW | P2 |
| Ladder gate rules | MEDIUM | MEDIUM | P2 |
| CLI compare command | MEDIUM | MEDIUM | P2 |
| Linearity analysis | MEDIUM | MEDIUM | P2 |
| Ramp-up period | LOW | LOW | P2 |
| Deterministic run IDs | LOW | LOW | P2 |
| 96 slots/day scenario | LOW | HIGH | P3 |
| Mixed message types | LOW | HIGH | P3 |
| Latency percentiles | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for first successful scaling ladder run
- P2: Should have for automated ladder execution and analysis
- P3: Nice to have, future phases

## Competitor Feature Analysis

| Feature | emqtt-bench | mqtt-benchmark (Go) | mqttloader | Gatling MQTT | This Tool |
|---------|-------------|---------------------|------------|--------------|-----------|
| Configurable connections | Yes (thousands) | Yes | Yes | Yes | Yes (asyncio tasks) |
| QoS selection | 0/1/2 | 0/1/2 | 0/1/2 | 0/1/2 | 0/1/2 |
| Rate limiting | Yes | Basic | No | Yes (injection profiles) | Yes (token bucket) |
| Custom payload content | Static/random bytes | Static string or file | Static/random | Template-based | Domain-aware factory with uniqueness |
| Per-message uniqueness | No (repeats same payload) | No | No | Possible via feeders | Yes (enforced by design) |
| Domain-specific payload schema | No | No | No | No | Yes (LP periodic envelope) |
| Real data input (CSV) | No | No | No | Yes (feeders) | Yes (core feature) |
| Time-slot semantics | No | No | No | No | Yes (slot planner) |
| Host resource telemetry | No | No | No | Partial (Gatling reports) | Yes (psutil sampling) |
| Structured run artifacts | No (stdout only) | Minimal | JSON summary | HTML report | Yes (run.json, summary.md, telemetry.csv, failed.jsonl) |
| Linearity analysis | No | No | No | No | Yes (cross-run comparison) |
| Scaling ladder automation | No | No | No | No (manual scenarios) | Yes (gate rules) |
| Ramp-up | No | No | No | Yes | Yes (planned) |
| Language | Erlang | Go | Java | Scala/Java | Python |

**Key insight from comparison:** No existing tool combines per-message uniqueness guarantees with domain-aware payload generation and scaling linearity analysis. The closest is Gatling with MQTT plugin + CSV feeders, but it requires JVM expertise, significant configuration, and does not model time-slot semantics or produce linearity reports.

## Sources

- Training data knowledge of: emqtt-bench (EMQX), mqtt-benchmark (kryukov/Go), mqttloader (dist-sys-practice), Gatling MQTT plugin, JMeter MQTT sampler, mqtt-stresser
- Project benchmark plan: `python-mqtt-benchmark.md` in this repository (primary source for domain-specific requirements)
- Confidence note: web search was unavailable during research. Feature comparisons are based on training data (cutoff ~early 2025). Tool capabilities may have changed. LOW confidence on competitor feature details; HIGH confidence on project-specific requirements derived from the benchmark plan.

---
*Feature research for: MQTT Load Generation / Benchmark Tooling*
*Researched: 2026-03-09*
