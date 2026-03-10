"""
Configuration schema and YAML loader for MQTT load generator scenarios.

This module provides data classes for scenario configuration and a YAML loader
with validation. It enables users to define broker settings, MQTT topics,
payload templates, and scenario parameters without code changes.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Dict, Any
from datetime import datetime, timezone

import yaml


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""

    pass


@dataclass
class BrokerConfig:
    """
    MQTT broker connection configuration.

    Attributes:
        host: Broker hostname or IP address
        port: Broker port number (default: 1883)
        tls: Enable TLS encryption (default: False)
        username: Optional username for authentication
        password: Optional password for authentication
    """

    host: str = "localhost"
    port: int = 1883
    tls: bool = False
    username: Optional[str] = None
    password: Optional[str] = None

    def __post_init__(self):
        """Validate broker configuration after initialization."""
        # Validate port is positive integer
        if not isinstance(self.port, int) or self.port <= 0:
            raise ConfigValidationError(
                f"Invalid port: {self.port} - must be a positive integer"
            )

        # Validate host is not empty
        if not self.host or not isinstance(self.host, str):
            raise ConfigValidationError(
                f"Invalid host: {self.host} - must be a non-empty string"
            )

        # Validate tls is boolean
        if not isinstance(self.tls, bool):
            raise ConfigValidationError(
                f"Invalid tls: {self.tls} - must be a boolean"
            )

        # Auto-set TLS port to 8883 only when using default port
        if self.tls and self.port == 1883:
            self.port = 8883


@dataclass
class MqttConfig:
    """
    MQTT-specific configuration.

    Attributes:
        topic: MQTT topic to publish to (default: "meter/loadProfile")
        qos: Quality of Service level (default: 1, must be 0/1/2)
    """

    topic: str = "meter/loadProfile"
    qos: int = 1

    def __post_init__(self):
        """Validate MQTT configuration after initialization."""
        # Validate QoS is 0, 1, or 2
        if self.qos not in (0, 1, 2):
            raise ConfigValidationError(
                f"Invalid QoS: {self.qos} - must be 0, 1, or 2"
            )

        # Validate topic is not empty
        if not self.topic or not isinstance(self.topic, str):
            raise ConfigValidationError(
                f"Invalid topic: {self.topic} - must be a non-empty string"
            )


@dataclass
class PayloadConfig:
    """
    Payload generation configuration.

    Attributes:
        dcu_id: Data Concentrator Unit ID (default: "DCU-001")
        meter_id_source: Path to CSV file containing meter IDs
        base_time: Optional base time for sampling_time calculation (ISO 8601 string)
    """

    dcu_id: str = "DCU-001"
    meter_id_source: Optional[str] = None
    base_time: Optional[str] = None

    def __post_init__(self):
        """Validate payload configuration after initialization."""
        # Validate dcu_id is not empty
        if not self.dcu_id or not isinstance(self.dcu_id, str):
            raise ConfigValidationError(
                f"Invalid dcu_id: {self.dcu_id} - must be a non-empty string"
            )

        # Validate meter_id_source file exists if provided
        if self.meter_id_source:
            meter_path = Path(self.meter_id_source)
            if not meter_path.exists():
                raise ConfigValidationError(
                    f"Meter ID source file not found: {self.meter_id_source}"
                )

        # Validate base_time if provided
        if self.base_time is not None:
            if not isinstance(self.base_time, str):
                raise ConfigValidationError(
                    f"Invalid base_time: {self.base_time} - must be a string"
                )
            # Try to parse it to validate ISO 8601 format
            try:
                self.get_base_time_datetime()
            except ValueError as e:
                raise ConfigValidationError(
                    f"Invalid base_time format: {e}"
                )

    def get_base_time_datetime(self) -> Optional[datetime]:
        """
        Convert base_time string to datetime object.

        Returns:
            datetime object in UTC if base_time is set, None otherwise

        Raises:
            ValueError: If base_time is not a valid ISO 8601 string
        """
        if self.base_time is None:
            return None

        # Handle 'Z' suffix (UTC indicator) for fromisoformat
        iso_string = self.base_time
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'

        try:
            dt = datetime.fromisoformat(iso_string)
            # Convert to UTC if timezone-aware
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc)
            else:
                # Assume UTC if no timezone specified
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError as e:
            raise ValueError(
                f"base_time must be a valid ISO 8601 datetime string (e.g., '2026-03-11T00:00:00Z'): {self.base_time}"
            )


@dataclass
class ScenarioConfig:
    """
    Complete scenario configuration for load generation.

    Attributes:
        name: Scenario name
        description: Optional scenario description
        message_count: Total number of messages to publish
        worker_count: Number of worker clients (default: 4)
        rate_limit: Maximum messages per second (must be positive)
        qos: Default QoS level (default: 1, must be 0/1/2)
        broker: Broker connection configuration
        mqtt: MQTT-specific configuration
        payload: Payload generation configuration
    """

    name: str
    message_count: int
    worker_count: int = 4
    rate_limit: int = 100
    qos: int = 1
    description: Optional[str] = None
    broker: Optional[BrokerConfig] = None
    mqtt: Optional[MqttConfig] = None
    payload: Optional[PayloadConfig] = None

    def __post_init__(self):
        """Validate scenario configuration after initialization."""
        # Validate required fields
        if not self.name or not isinstance(self.name, str):
            raise ConfigValidationError(
                f"Invalid name: {self.name} - must be a non-empty string"
            )

        # Validate message_count is positive integer
        if not isinstance(self.message_count, int) or self.message_count <= 0:
            raise ConfigValidationError(
                f"Invalid message_count: {self.message_count} - must be a positive integer"
            )

        # Validate worker_count is positive integer
        if not isinstance(self.worker_count, int) or self.worker_count <= 0:
            raise ConfigValidationError(
                f"Invalid worker_count: {self.worker_count} - must be a positive integer"
            )

        # Validate rate_limit is positive integer
        if not isinstance(self.rate_limit, int) or self.rate_limit <= 0:
            raise ConfigValidationError(
                f"Invalid rate_limit: {self.rate_limit} - must be a positive integer"
            )

        # Validate QoS is 0, 1, or 2
        if self.qos not in (0, 1, 2):
            raise ConfigValidationError(
                f"Invalid QoS: {self.qos} - must be 0, 1, or 2"
            )

        # Create default configs if not provided
        if self.broker is None:
            self.broker = BrokerConfig()
        elif isinstance(self.broker, dict):
            self.broker = BrokerConfig(**self.broker)

        if self.mqtt is None:
            self.mqtt = MqttConfig()
        elif isinstance(self.mqtt, dict):
            self.mqtt = MqttConfig(**self.mqtt)

        if self.payload is None:
            self.payload = PayloadConfig()
        elif isinstance(self.payload, dict):
            self.payload = PayloadConfig(**self.payload)


def load_config(config_path: Union[str, Path]) -> ScenarioConfig:
    """
    Load scenario configuration from YAML file.

    Args:
        config_path: Path to YAML configuration file

    Returns:
        ScenarioConfig instance with validated configuration

    Raises:
        FileNotFoundError: If configuration file not found
        ConfigValidationError: If YAML is invalid or validation fails
    """
    config_path = Path(config_path)

    # Validate file exists
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load YAML file
    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigValidationError(f"Invalid YAML syntax: {e}")
    except Exception as e:
        raise ConfigValidationError(f"Failed to read configuration file: {e}")

    if not data:
        raise ConfigValidationError("Configuration file is empty")

    # Validate required fields
    required_fields = ["name", "message_count", "rate_limit"]
    for field in required_fields:
        if field not in data:
            raise ConfigValidationError(f"Missing required field: {field}")

    # Extract broker configuration
    broker_data = data.get("broker", {})
    if not isinstance(broker_data, dict):
        raise ConfigValidationError("Invalid broker section - must be a dictionary")

    # Extract mqtt configuration
    mqtt_data = data.get("mqtt", {})
    if not isinstance(mqtt_data, dict):
        raise ConfigValidationError("Invalid mqtt section - must be a dictionary")

    # Extract payload configuration
    payload_data = data.get("payload", {})
    if not isinstance(payload_data, dict):
        raise ConfigValidationError("Invalid payload section - must be a dictionary")

    # Validate and create configs
    try:
        # Create broker config
        broker_config = BrokerConfig(
            host=broker_data.get("host", "localhost"),
            port=broker_data.get("port", 1883),
            tls=broker_data.get("tls", False),
            username=broker_data.get("username"),
            password=broker_data.get("password"),
        )

        # Create MQTT config
        mqtt_config = MqttConfig(
            topic=mqtt_data.get("topic", "meter/loadProfile"),
            qos=mqtt_data.get("qos", 1),
        )

        # Create payload config
        payload_config = PayloadConfig(
            dcu_id=payload_data.get("dcu_id", "DCU-001"),
            meter_id_source=payload_data.get("meter_id_source"),
            base_time=payload_data.get("base_time"),
        )

        # Create scenario config
        scenario_config = ScenarioConfig(
            name=data["name"],
            description=data.get("description"),
            message_count=data["message_count"],
            worker_count=data.get("worker_count", 4),
            rate_limit=data["rate_limit"],
            qos=data.get("qos", 1),
            broker=broker_config,
            mqtt=mqtt_config,
            payload=payload_config,
        )

        return scenario_config

    except (TypeError, ValueError) as e:
        raise ConfigValidationError(f"Invalid configuration value: {e}")
    except ConfigValidationError:
        # Re-raise ConfigValidationError as-is
        raise
    except Exception as e:
        raise ConfigValidationError(f"Unexpected error loading configuration: {e}")
