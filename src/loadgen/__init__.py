"""
Python MQTT Load Generator

A load testing tool for MQTT brokers that publishes realistic
Load Profile periodic events to benchmark data-collection services.
"""

# Export key modules for easy importing
from loadgen.csv_reader import load_meter_ids, MeterIdValidationError
from loadgen.mqtt_client import MQTTClient, MQTTConnectionError, MQTTPublishError
from loadgen.worker_pool import WorkerPool, WorkerConnectionError
from loadgen.rate_limiter import TokenBucketRateLimiter
from loadgen.retry_policy import (
    RetryPolicy,
    RetryableError,
    NonRetryableError,
    MaxRetriesExceededError,
    BackoffStrategy,
)
from loadgen.publisher import Publisher, PublishInterruptError
from loadgen.payload import PayloadFactory
from loadgen.slot_planner import SlotPlanner
from loadgen.config import (
    load_config,
    ScenarioConfig,
    BrokerConfig,
    MqttConfig,
    PayloadConfig,
    ConfigValidationError,
)
from loadgen.cli import cli

__all__ = [
    "load_meter_ids",
    "MeterIdValidationError",
    "MQTTClient",
    "MQTTConnectionError",
    "MQTTPublishError",
    "WorkerPool",
    "WorkerConnectionError",
    "TokenBucketRateLimiter",
    "RetryPolicy",
    "RetryableError",
    "NonRetryableError",
    "MaxRetriesExceededError",
    "BackoffStrategy",
    "Publisher",
    "PublishInterruptError",
    "PayloadFactory",
    "SlotPlanner",
    "load_config",
    "ScenarioConfig",
    "BrokerConfig",
    "MqttConfig",
    "PayloadConfig",
    "ConfigValidationError",
    "cli",
]


if __name__ == "__main__":
    cli()
