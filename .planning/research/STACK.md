# Technology Stack

**Project:** Python MQTT Load Generator
**Researched:** 2026-03-09
**Overall Confidence:** HIGH (all versions verified against PyPI)

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | >=3.11 | Runtime | Required for `asyncio.TaskGroup`, `tomllib`, and performance improvements in the 3.11+ asyncio event loop (10-20% faster). The system Python 3.9.6 on this Mac is too old -- use pyenv or brew to install 3.11+. | HIGH |
| uvloop | 0.22.1 | Event loop replacement | Drop-in libuv-based event loop, 2-4x faster than the default asyncio loop for I/O-heavy workloads. Critical for sustaining 200k publishes. Not available on Windows but irrelevant (M1 Mac target). | HIGH |

### Core Libraries

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| aiomqtt | 2.5.1 | Async MQTT client | The only maintained async MQTT 5.0/3.1.1 client for Python. Wraps paho-mqtt with a clean asyncio context-manager API. Supports QoS 1 with proper ack tracking. No serious alternative exists -- gmqtt is abandoned. | HIGH |
| paho-mqtt | (transitive) | MQTT protocol engine | Installed automatically as aiomqtt's dependency. Do NOT import directly -- use only through aiomqtt's async wrapper. | HIGH |
| orjson | 3.11.5 | JSON serialization | 3-10x faster than stdlib `json` for encoding payloads. At 200k events, the serialization cost adds up. Returns `bytes` directly (no encode step), which MQTT publish accepts natively. | HIGH |
| PyYAML | 6.0.3 | Config file parsing | Standard YAML parser. Use `yaml.safe_load()` only -- never `yaml.load()`. Scenario configs (1k/5k/10k profiles) are naturally expressed as YAML. | HIGH |
| pydantic | 2.12.5 | Config validation and payload models | Validates YAML config into typed Python objects with clear error messages. Pydantic v2 is Rust-backed and fast enough for config-time validation. Also useful for payload envelope schema enforcement. | HIGH |
| psutil | 7.2.2 | Resource telemetry | Cross-platform CPU%, RSS memory, and process-level metrics. The standard tool for this -- no alternative comes close. Sample at 1-second intervals into telemetry.csv. | HIGH |
| aiofiles | 25.1.0 | Async file I/O | Non-blocking writes for telemetry CSV and failed_events.jsonl during benchmark runs. Prevents file I/O from stalling the publish loop. | HIGH |

### CLI and Output

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| typer | 0.23.2 | CLI framework | Built on click but with type-hint-driven argument parsing. Clean subcommand support for `run`, `compare`, `list-scenarios`. Rich integration for pretty output. | HIGH |
| rich | 14.3.3 | Terminal output | Live progress bars during publish, formatted tables for results summary, colored logging. Typer uses it automatically when installed. | HIGH |
| structlog | 25.5.0 | Structured logging | JSON-structured logs for machine parsing, pretty console output for humans. Async-safe. Better than stdlib logging for correlating run metadata (scenario, timestamp, worker count). | MEDIUM |

### CSV and Data

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| csv (stdlib) | -- | CSV reading | Stdlib `csv.DictReader` is sufficient for reading meter IDs from CSV. No need for pandas -- the CSV is a simple ID list, not a data analysis task. | HIGH |

### Dev and Quality

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| ruff | 0.15.5 | Linter + formatter | Replaces flake8, isort, black in a single Rust-based tool. 100x faster than the tools it replaces. Industry standard for new Python projects in 2025+. | HIGH |
| mypy | 1.19.1 | Type checking | Static type analysis. Use strict mode. Catches async/await mistakes before runtime. | HIGH |
| pytest | 8.4.2 | Testing | Standard test runner. | HIGH |
| pytest-asyncio | (latest) | Async test support | Required for testing async MQTT publish functions. Use `mode = "auto"` in pytest config. | HIGH |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| MQTT Client | aiomqtt 2.5.1 | gmqtt | Abandoned since 2021, no maintenance, missing MQTT 5 features |
| MQTT Client | aiomqtt 2.5.1 | paho-mqtt (direct) | Synchronous API requires threading; aiomqtt wraps it properly for asyncio |
| MQTT Client | aiomqtt 2.5.1 | FastMQTT | Web framework integration (FastAPI); wrong abstraction for a load generator |
| JSON | orjson 3.11.5 | ujson | Slower than orjson, fewer features, less maintained |
| JSON | orjson 3.11.5 | stdlib json | 3-10x slower; at 200k payloads the difference is measurable seconds |
| Config | PyYAML + pydantic | toml (stdlib) | YAML is more natural for nested scenario configs with lists/maps; TOML gets verbose |
| Config | PyYAML + pydantic | dataclasses | No built-in validation, no YAML deserialization, error messages are poor |
| Config | PyYAML + pydantic | attrs | Viable but pydantic has better ecosystem adoption and JSON schema generation |
| CLI | typer 0.23.2 | click 8.1.8 | Typer wraps click with less boilerplate; same power, better DX |
| CLI | typer 0.23.2 | argparse (stdlib) | Verbose, no auto-completion, no rich integration, painful for subcommands |
| Telemetry | psutil 7.2.2 | /proc parsing | Not cross-platform, fragile, reinventing the wheel |
| Logging | structlog 25.5.0 | stdlib logging | Lacks structured output, harder to correlate run metadata |
| Formatter | ruff 0.15.5 | black + isort + flake8 | Three tools vs one, 100x slower, more config to maintain |
| Event loop | uvloop 0.22.1 | stdlib asyncio | 2-4x slower for I/O-bound workloads; free performance on Unix |
| Async files | aiofiles 25.1.0 | sync writes in executor | aiofiles does exactly this but with a cleaner API |

## What NOT to Use

| Library | Why Not |
|---------|---------|
| pandas | Massive dependency for reading a simple CSV of meter IDs. Overkill. Use stdlib csv. |
| asyncio-mqtt | Old name for aiomqtt (pre-rename). Use aiomqtt. |
| gmqtt | Abandoned. Last release 2021. |
| paho-mqtt (direct) | Synchronous. Forces you into threading which defeats the asyncio architecture. |
| celery / dramatiq | Task queue overhead for what is a tight publish loop. asyncio.TaskGroup is sufficient. |
| httpx / aiohttp | No HTTP in this project. MQTT only. |
| numpy | No numerical computation needed. |
| docker-py | Broker management is out of scope per PROJECT.md. |

## Python Version Strategy

The system Python on this MacBook is 3.9.6 which is too old. The project MUST use Python 3.11+ for:

1. **`asyncio.TaskGroup`** -- structured concurrency for managing worker tasks (3.11+)
2. **`ExceptionGroup`** -- proper error handling when multiple workers fail (3.11+)
3. **Event loop performance** -- CPython 3.11 has measurably faster asyncio internals
4. **`tomllib`** -- stdlib TOML if needed later (3.11+)

Recommend Python 3.12 or 3.13 via pyenv. Add `.python-version` file to the repo.

## Project Structure

```
python-loadgen/
  pyproject.toml          # Single config file (no setup.py, no setup.cfg)
  src/
    loadgen/
      __init__.py
      cli.py              # Typer CLI entry point
      config.py           # Pydantic models for YAML config
      publisher.py        # Async MQTT publish engine
      payload.py          # LP periodic payload generation
      telemetry.py        # psutil resource sampling
      csv_reader.py       # Meter ID loading from CSV
      artifacts.py        # Run output (run.json, telemetry.csv, summary.md)
      analysis.py         # Linearity comparison across runs
  scenarios/
    scenario_1k.yaml
    scenario_5k.yaml
    scenario_10k.yaml
  tests/
  data/
    meter_ids.csv         # Real meter IDs
```

## Installation

```bash
# Create virtual environment (use Python 3.12+)
python3.12 -m venv .venv
source .venv/bin/activate

# Core dependencies
pip install aiomqtt==2.5.1 orjson==3.11.5 pyyaml==6.0.3 pydantic==2.12.5 \
           psutil==7.2.2 aiofiles==25.1.0 uvloop==0.22.1 \
           typer==0.23.2 rich==14.3.3 structlog==25.5.0

# Dev dependencies
pip install -D ruff==0.15.5 mypy==1.19.1 pytest==8.4.2 pytest-asyncio
```

Or in `pyproject.toml`:

```toml
[project]
name = "python-loadgen"
requires-python = ">=3.11"
dependencies = [
    "aiomqtt>=2.5,<3",
    "orjson>=3.11,<4",
    "pyyaml>=6,<7",
    "pydantic>=2.12,<3",
    "psutil>=7,<8",
    "aiofiles>=25,<26",
    "uvloop>=0.22; sys_platform != 'win32'",
    "typer>=0.23,<1",
    "rich>=14,<15",
    "structlog>=25,<26",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.15",
    "mypy>=1.19",
    "pytest>=8",
    "pytest-asyncio",
]

[project.scripts]
loadgen = "loadgen.cli:app"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Key Integration Notes

### aiomqtt Usage Pattern

```python
import asyncio
import aiomqtt

async def publish_batch(broker: str, port: int, messages: list[dict]):
    async with aiomqtt.Client(broker, port=port) as client:
        async with asyncio.TaskGroup() as tg:
            for msg in messages:
                tg.create_task(client.publish(topic, payload=orjson.dumps(msg), qos=1))
```

**Important:** aiomqtt uses a single TCP connection per `Client` instance. For concurrent publishing, use multiple `Client` instances across workers (one per asyncio task), NOT one shared client. The paho-mqtt layer underneath is not designed for concurrent publishes on the same connection.

### uvloop Activation

```python
# In cli.py or __main__.py, before any asyncio.run():
import uvloop
uvloop.install()  # Replaces default event loop globally
```

### psutil Telemetry Sampling

```python
import psutil, time

def sample() -> dict:
    proc = psutil.Process()
    return {
        "timestamp": time.time(),
        "cpu_percent": proc.cpu_percent(),
        "rss_mb": proc.memory_info().rss / 1_048_576,
        "threads": proc.num_threads(),
    }
```

## Sources

All version numbers verified against PyPI index on 2026-03-09 using `pip3 index versions`.

- aiomqtt: https://pypi.org/project/aiomqtt/ (v2.5.1, wraps paho-mqtt)
- orjson: https://pypi.org/project/orjson/ (v3.11.5, Rust-based JSON)
- pydantic: https://pypi.org/project/pydantic/ (v2.12.5, Rust-backed validation)
- psutil: https://pypi.org/project/psutil/ (v7.2.2, system monitoring)
- uvloop: https://pypi.org/project/uvloop/ (v0.22.1, libuv event loop)
- typer: https://pypi.org/project/typer/ (v0.23.2, CLI framework)
- rich: https://pypi.org/project/rich/ (v14.3.3, terminal formatting)
- structlog: https://pypi.org/project/structlog/ (v25.5.0, structured logging)
- aiofiles: https://pypi.org/project/aiofiles/ (v25.1.0, async file I/O)
- ruff: https://pypi.org/project/ruff/ (v0.15.5, linter/formatter)
