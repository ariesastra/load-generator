"""Tests for MQTT client wrapper."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from loadgen.mqtt_client import MQTTClient, MQTTConnectionError, MQTTPublishError


class TestMQTTClientInit:
    """Test MQTTClient initialization and configuration."""

    def test_client_accepts_connection_config(self):
        """Test 1: Client accepts host, port, qos, tls_enabled, username, password."""
        client = MQTTClient(
            host="localhost",
            port=1883,
            qos=1,
            tls_enabled=False,
            username="user",
            password="pass"
        )
        assert client._host == "localhost"
        assert client._port == 1883
        assert client._qos == 1
        assert client._tls_enabled is False
        assert client._username == "user"
        assert client._password == "pass"

    def test_qos_must_be_0_1_or_2(self):
        """Test 2: QoS must be 0, 1, or 2 (ValueError otherwise)."""
        with pytest.raises(ValueError, match="QoS must be 0, 1, or 2"):
            MQTTClient(host="localhost", qos=3)

        with pytest.raises(ValueError, match="QoS must be 0, 1, or 2"):
            MQTTClient(host="localhost", qos=-1)

        # Valid QoS values should not raise
        MQTTClient(host="localhost", qos=0)
        MQTTClient(host="localhost", qos=1)
        MQTTClient(host="localhost", qos=2)

    def test_tls_enabled_sets_port_8883_if_not_explicit(self):
        """Test 3: TLS enabled sets port to 8883 if not explicitly set."""
        # When TLS is enabled and port is default, should use 8883
        client_tls = MQTTClient(host="localhost", tls_enabled=True)
        assert client_tls._port == 8883

        # When TLS is enabled and port is explicitly set, should use that port
        client_tls_custom = MQTTClient(host="localhost", tls_enabled=True, port=8884)
        assert client_tls_custom._port == 8884

        # When TLS is disabled, should use default 1883
        client_no_tls = MQTTClient(host="localhost", tls_enabled=False)
        assert client_no_tls._port == 1883


class TestMQTTClientConnection:
    """Test MQTTClient connection lifecycle."""

    @pytest.mark.asyncio
    async def test_connect_establishes_connection_using_aiomqtt(self):
        """Test 4: async connect() establishes connection using aiomqtt.Client context manager."""
        with patch('loadgen.mqtt_client.aiomqtt.Client') as mock_client_class:
            # Setup mock
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MQTTClient(host="localhost", port=1883)
            await client.connect()

            # Verify aiomqtt.Client was called with correct parameters
            mock_client_class.assert_called_once()
            call_kwargs = mock_client_class.call_args[1]
            assert call_kwargs['hostname'] == "localhost"
            assert call_kwargs['port'] == 1883
            assert client._connected is True
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_disconnect_sends_graceful_disconnect(self):
        """Test 5: async disconnect() sends graceful DISCONNECT packet."""
        with patch('loadgen.mqtt_client.aiomqtt.Client') as mock_client_class:
            # Setup mock
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MQTTClient(host="localhost")
            await client.connect()
            await client.disconnect()

            # Verify disconnect was called
            assert client._connected is False

    @pytest.mark.asyncio
    async def test_connection_failure_raises_mqtt_connection_error(self):
        """Test 6: Connection failure raises MQTTConnectionError."""
        with patch('loadgen.mqtt_client.aiomqtt.Client') as mock_client_class:
            # Setup mock to raise exception during __aenter__
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            client = MQTTClient(host="localhost")
            with pytest.raises(MQTTConnectionError, match="Failed to connect to MQTT broker"):
                await client.connect()

            assert client._connected is False


class TestMQTTClientPublish:
    """Test MQTTClient publish functionality."""

    @pytest.mark.asyncio
    async def test_publish_calls_client_publish_with_configured_qos(self):
        """Test 1: publish() calls client.publish with configured QoS level."""
        with patch('loadgen.mqtt_client.aiomqtt.Client') as mock_client_class:
            # Setup mock
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.publish = AsyncMock()
            mock_client_class.return_value = mock_client

            # Test with QoS 0
            client_qos0 = MQTTClient(host="localhost", qos=0)
            await client_qos0.connect()
            await client_qos0.publish("test/topic", b"payload")
            mock_client.publish.assert_called_with("test/topic", payload=b"payload", qos=0)

            # Test with QoS 1
            mock_client.publish.reset_mock()
            client_qos1 = MQTTClient(host="localhost", qos=1)
            await client_qos1.connect()
            await client_qos1.publish("test/topic", b"payload")
            mock_client.publish.assert_called_with("test/topic", payload=b"payload", qos=1)

            # Test with QoS 2
            mock_client.publish.reset_mock()
            client_qos2 = MQTTClient(host="localhost", qos=2)
            await client_qos2.connect()
            await client_qos2.publish("test/topic", b"payload")
            mock_client.publish.assert_called_with("test/topic", payload=b"payload", qos=2)

    @pytest.mark.asyncio
    async def test_publish_converts_string_payload_to_bytes(self):
        """Test 6: Payload is converted to bytes if string."""
        with patch('loadgen.mqtt_client.aiomqtt.Client') as mock_client_class:
            # Setup mock
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.publish = AsyncMock()
            mock_client_class.return_value = mock_client

            client = MQTTClient(host="localhost")
            await client.connect()
            await client.publish("test/topic", "string payload")

            # Verify payload was converted to bytes
            mock_client.publish.assert_called_once()
            call_args = mock_client.publish.call_args
            assert call_args[0][0] == "test/topic"
            assert call_args[1]['payload'] == b"string payload"

    @pytest.mark.asyncio
    async def test_publish_failure_raises_mqtt_publish_error(self):
        """Test 5: Publish failure raises MQTTPublishError."""
        with patch('loadgen.mqtt_client.aiomqtt.Client') as mock_client_class:
            # Setup mock
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.publish = AsyncMock(side_effect=Exception("Publish failed"))
            mock_client_class.return_value = mock_client

            client = MQTTClient(host="localhost")
            await client.connect()

            with pytest.raises(MQTTPublishError, match="Failed to publish message"):
                await client.publish("test/topic", b"payload")

    @pytest.mark.asyncio
    async def test_publish_when_not_connected_raises_error(self):
        """Test: Publishing when not connected raises MQTTConnectionError."""
        client = MQTTClient(host="localhost")

        with pytest.raises(MQTTConnectionError, match="Cannot publish: client is not connected"):
            await client.publish("test/topic", b"payload")
