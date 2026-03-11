# Aegis MQTT Load Generator

A Python-based load testing tool for benchmarking MQTT message brokers.

## Installation

### Development Installation

```bash
# Install in editable mode
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## Usage

### Run a benchmark scenario

```bash
# Using the installed CLI
loadgen run --scenario scenarios/scenario_1k.yaml

# Or using Python module
cd src/
python3 -m loadgen run --scenario scenarios/scenario_1k.yaml

# Dry run (no actual messages sent)
loadgen run --dry-run --scenario scenarios/scenario_1k.yaml
```

### Scenario Configuration

Scenario files are YAML documents that define:

- **Broker settings**: MQTT broker host and port
- **MQTT settings**: Topic, QoS level
- **Load profile**: Message count, worker count, rate limit
- **Payload factory**: DCU ID, meter ID source

Example scenarios are provided in the `scenarios/` directory.

## Development

### Running Tests

```bash
pytest
```

### Project Structure

```
src/loadgen/
├── __init__.py      # Package exports
├── __main__.py      # Entry point for python -m loadgen
├── cli.py           # Click-based CLI
├── config.py        # Configuration schema and YAML loader
├── mqtt_client.py   # MQTT client wrapper
├── payload.py       # Payload generation
├── publisher.py     # Publishing orchestrator
├── retry_policy.py  # Retry strategies
└── worker_pool.py   # Worker pool management
```

## License

MIT
