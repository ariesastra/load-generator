"""
Click-based CLI interface for MQTT load generator.

This module provides the command-line interface for running benchmark
scenarios from YAML configuration files.
"""

import asyncio
import click
from pathlib import Path
from typing import Optional, Dict, Any

from loadgen import load_config, Publisher
import loadgen.csv_reader as csv_reader


@click.group()
def cli():
    """Python MQTT Load Generator - Benchmark MQTT brokers with realistic LP periodic events."""
    pass


@cli.command()
@click.argument("scenario", type=click.Path(exists=True, path_type=Path))
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--dry-run", is_flag=True, help="Validate configuration without running benchmark")
def run(scenario: Path, verbose: bool, dry_run: bool):
    """Run benchmark scenario from YAML configuration file.

    SCENARIO is the path to the YAML configuration file.

    Example:
        loadgen run --scenario scenario_1k.yaml
    """
    # Load configuration
    try:
        config = load_config(scenario)
        click.echo(f"Loaded scenario: {config.name}")
        if dry_run:
            click.echo("Configuration validated successfully (dry run)")
            return
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        raise click.Abort()

    # Load meter IDs from CSV
    try:
        meter_ids = csv_reader.load_meter_ids(config.payload.meter_id_source)
        click.echo(f"Loaded {len(meter_ids)} meter IDs")
    except Exception as e:
        click.echo(f"Error loading meter IDs: {e}", err=True)
        raise click.Abort()

    # Run publisher (async)
    try:
        stats = asyncio.run(_run_publisher(config, meter_ids, verbose))
        _print_summary(stats)
    except KeyboardInterrupt:
        click.echo("\nBenchmark interrupted by user")
    except Exception as e:
        click.echo(f"Error during benchmark: {e}", err=True)
        raise click.Abort()


async def _run_publisher(
    config,
    meter_ids: list[str],
    verbose: bool
) -> Dict[str, Any]:
    """Initialize and run Publisher with configuration."""
    # Parse base_time from config
    base_time = config.payload.get_base_time_datetime()

    publisher = Publisher(
        broker_config={
            "host": config.broker.host,
            "port": config.broker.port,
            "tls_enabled": config.broker.tls,
            "username": config.broker.username,
            "password": config.broker.password,
        },
        worker_count=config.worker_count,
        message_count=config.message_count,
        rate_limit=config.rate_limit,
        qos=config.mqtt.qos,
        meter_ids=meter_ids,
        dcu_id=config.payload.dcu_id,
        topic=config.mqtt.topic,
        base_time=base_time,
    )
    return await publisher.run()


def _print_summary(stats: Dict[str, Any]) -> None:
    """Print benchmark summary statistics."""
    click.echo("\n" + "="*60)
    click.echo("Benchmark Complete")
    click.echo("="*60)
    click.echo(f"Messages sent:     {stats.get('sent', 0)}")
    click.echo(f"Messages failed:   {stats.get('failed', 0)}")
    click.echo(f"Duration:          {stats.get('duration', 0):.2f} seconds")
    if stats.get('sent', 0) > 0:
        throughput = stats.get('sent', 0) / stats.get('duration', 1)
        click.echo(f"Throughput:        {throughput:.2f} msg/sec")
    click.echo("="*60)
