"""
Python MQTT Load Generator

A load testing tool for MQTT brokers that publishes realistic
Load Profile periodic events to benchmark data-collection services.
"""

# Export key modules for easy importing
from loadgen.csv_reader import load_meter_ids, MeterIdValidationError
from loadgen.mqtt_client import MQTTClient, MQTTConnectionError, MQTTPublishError
from loadgen.worker_pool import WorkerPool, WorkerConnectionError

# Note: These modules will be implemented in subsequent plans
# from loadgen.payload import PayloadFactory
# from loadgen.slot_planner import SlotPlanner

__all__ = [
    "load_meter_ids",
    "MeterIdValidationError",
    "MQTTClient",
    "MQTTConnectionError",
    "MQTTPublishError",
    "WorkerPool",
    "WorkerConnectionError",
    # "PayloadFactory",  # To be implemented in plan 01-03
    # "SlotPlanner",  # To be implemented in plan 01-04
]
