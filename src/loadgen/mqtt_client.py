"""Async MQTT client wrapper using aiomqtt.

This module provides MQTTClient class for broker connections with
configurable TLS, authentication, and QoS levels.
"""

import ssl
from typing import Optional, Union

import aiomqtt


class MQTTConnectionError(Exception):
    """Raised when MQTT connection fails."""

    pass


class MQTTPublishError(Exception):
    """Raised when MQTT publish fails."""

    pass


class MQTTClient:
    """Async MQTT client wrapper using aiomqtt."""

    def __init__(
        self,
        host: str,
        port: int = 1883,
        qos: int = 1,
        tls_enabled: bool = False,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """Initialize MQTT client configuration.

        Args:
            host: MQTT broker hostname or IP
            port: MQTT broker port (1883 for plain, 8883 for TLS)
            qos: QoS level (0, 1, or 2)
            tls_enabled: Whether to use TLS/SSL
            username: Optional username for authentication
            password: Optional password for authentication

        Raises:
            ValueError: If qos not in (0, 1, 2)
        """
        if qos not in (0, 1, 2):
            raise ValueError(f"QoS must be 0, 1, or 2, got {qos}")

        self._host = host
        # Auto-set port to 8883 if TLS is enabled and port wasn't explicitly changed
        if tls_enabled and port == 1883:
            self._port = 8883
        else:
            self._port = port
        self._qos = qos
        self._tls_enabled = tls_enabled
        self._username = username
        self._password = password

        # Internal state
        self._client: Optional[aiomqtt.Client] = None
        self._connected: bool = False

    async def connect(self) -> None:
        """Establish connection to MQTT broker.

        Raises:
            MQTTConnectionError: If connection fails
        """
        try:
            # Prepare TLS context if enabled
            tls_context = None
            if self._tls_enabled:
                tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            # Create aiomqtt client with configuration
            self._client = aiomqtt.Client(
                hostname=self._host,
                port=self._port,
                tls_context=tls_context,
                username=self._username,
                password=self._password,
            )

            # Establish connection using context manager
            await self._client.__aenter__()
            self._connected = True

        except Exception as e:
            self._connected = False
            self._client = None
            raise MQTTConnectionError(f"Failed to connect to MQTT broker: {e}") from e

    async def disconnect(self) -> None:
        """Gracefully disconnect from broker."""
        if self._client is not None and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                # Ignore errors during disconnect
                pass
            finally:
                self._connected = False
                self._client = None

    async def publish(self, topic: str, payload: Union[bytes, str]) -> None:
        """Publish message to topic.

        Args:
            topic: MQTT topic to publish to
            payload: Message payload (bytes or string)

        Raises:
            MQTTConnectionError: If client is not connected
            MQTTPublishError: If publish fails
        """
        if not self._connected or self._client is None:
            raise MQTTConnectionError("Cannot publish: client is not connected")

        # Convert string payload to bytes
        if isinstance(payload, str):
            payload = payload.encode("utf-8")

        try:
            await self._client.publish(topic, payload=payload, qos=self._qos)
        except Exception as e:
            raise MQTTPublishError(f"Failed to publish message: {e}") from e
