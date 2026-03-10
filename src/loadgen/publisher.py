"""
Publisher orchestrator for MQTT load generation.

This module provides the Publisher class that orchestrates the full publishing
workflow, coordinating WorkerPool, RateLimiter, RetryPolicy, and PayloadFactory
to generate and publish MQTT messages with graceful shutdown handling.

Key features:
- Coordinates WorkerPool, TokenBucketRateLimiter, and RetryPolicy integration
- Generates payloads using PayloadFactory
- Manages full publish workflow: initialize → publish → cleanup
- Handles KeyboardInterrupt with immediate abort and graceful DISCONNECT
- Writes partial artifacts (run.json) on interruption
- Supports double Ctrl+C for force quit
"""

import asyncio
import json
import signal
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import structlog

from loadgen.worker_pool import WorkerPool, MQTTClient
from loadgen.rate_limiter import TokenBucketRateLimiter
from loadgen.retry_policy import (
    RetryPolicy,
    RetryableError,
    NonRetryableError,
    MaxRetriesExceededError,
    BackoffStrategy,
)
from loadgen.payload import PayloadFactory
import loadgen.csv_reader as csv_reader


logger = structlog.get_logger(__name__)


class PublishInterruptError(Exception):
    """Exception raised when publishing is interrupted by user (Ctrl+C)."""

    pass


class Publisher:
    """
    Publisher orchestrator for MQTT load generation.

    Orchestrates the full publishing workflow with graceful shutdown handling.
    Integrates WorkerPool, RateLimiter, RetryPolicy, and PayloadFactory.
    """

    def __init__(
        self,
        broker_config: Dict[str, Any],
        worker_count: int,
        message_count: int,
        rate_limit: Optional[int] = None,
        retry_config: Optional[Dict[str, Any]] = None,
        artifact_dir: Optional[Union[str, Path]] = None,
        meter_ids_csv: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize Publisher orchestrator.

        Args:
            broker_config: MQTT broker connection config
            worker_count: Number of worker clients
            message_count: Total messages to publish
            rate_limit: Max publish rate per second (None = unlimited)
            retry_config: Retry policy configuration
            artifact_dir: Directory for writing artifacts
            meter_ids_csv: Path to CSV with meter IDs (default: Asset-Meter.csv)
        """
        self.broker_config = broker_config
        self.worker_count = worker_count
        self.message_count = message_count
        self.rate_limit = rate_limit
        self.retry_config = retry_config or {}
        self.artifact_dir = Path(artifact_dir) if artifact_dir else None
        self.meter_ids_csv = Path(meter_ids_csv) if meter_ids_csv else None
        self._interrupted = False

        # Initialize components
        # Create retry policy if config provided
        retry_policy = None
        if retry_config:
            max_retries = retry_config.get("max_retries", 3)
            base_delay = retry_config.get("base_delay", 1.0)
            max_delay = retry_config.get("max_delay", 5.0)
            multiplier = retry_config.get("multiplier", 2.0)

            retry_policy = RetryPolicy(
                max_retries=max_retries,
                strategy=BackoffStrategy.EXPONENTIAL,
                base_delay=base_delay,
                multiplier=multiplier,
            )

        # Create rate limiter if rate_limit specified
        rate_limiter = (
            TokenBucketRateLimiter(rate_limit=rate_limit) if rate_limit else None
        )

        self._worker_pool = WorkerPool(
            worker_count=worker_count,
            broker_config=broker_config,
            retry_policy=retry_policy,
            rate_limiter=rate_limiter,
        )

        # Initialize payload factory
        self._payload_factory = PayloadFactory()

        # Initialize meter IDs (load lazy or use sample)
        self._meter_ids: List[str] = []

        # Track interrupt count for double Ctrl+C handling
        self._interrupt_count = 0
        self._last_interrupt_time = 0.0

    async def run(self, topic: str = "load-profile") -> Dict[str, Any]:
        """
        Run the full publishing workflow.

        Orchestrates:
        1. Initialize worker pool
        2. Generate payloads
        3. Publish messages
        4. Cleanup workers

        Args:
            topic: MQTT topic to publish to

        Returns:
            Dict with stats: sent, failed, duration

        Raises:
            PublishInterruptError: If publishing is interrupted
        """
        start_time = time.time()
        stats: Dict[str, Any] = {"sent": 0, "failed": 0, "duration": 0.0}

        try:
            # Initialize worker pool
            logger.info("Initializing worker pool", worker_count=self.worker_count)
            await self._worker_pool.initialize()

            # Generate payloads
            logger.info(
                "Generating payloads", message_count=self.message_count
            )
            messages = await self._generate_payloads()

            # Publish messages (unless interrupted)
            if not self._interrupted:
                logger.info(
                    f"Publishing {len(messages)} messages to topic '{topic}'"
                )
                publish_result = await self._worker_pool.publish(
                    messages=messages, topic=topic
                )
                stats.update(publish_result)

            else:
                logger.warning(
                    "Skipping publish (already interrupted)"
                )
                # Still need to cleanup
                await self._worker_pool.cleanup()

        except KeyboardInterrupt:
            await self._handle_interrupt(stats=stats, start_time=start_time)

        except Exception as e:
            logger.error("Unexpected error during publish", error=str(e))
            # Still try to cleanup on error
            await self._shutdown(stats=stats, start_time=start_time)
            raise

        finally:
            # Always cleanup on normal completion
            if not self._interrupted:
                logger.info("Normal completion - cleaning up worker pool")
                await self._worker_pool.cleanup()

        # Calculate duration
        stats["duration"] = time.time() - start_time

        logger.info("Publishing complete", stats=stats)
        return stats

    async def _generate_payloads(self) -> List[bytes]:
        """
        Generate payloads for publishing.

        For Phase 2, we'll use sample meter IDs. Full CSV loading comes in Phase 3.

        Returns:
            List of payload bytes
        """
        # Load meter IDs (sample for now)
        if not self._meter_ids:
            self._meter_ids = ["123456789000", "123456789001"]

        messages = []
        slot_index = 0

        # Generate payloads round-robin across meter IDs
        for i in range(self.message_count):
            meter_id = self._meter_ids[i % len(self._meter_ids)]

            # Generate payload using factory
            payload = self._payload_factory.generate_payload(
                meter_id=meter_id, slot_index=slot_index
            )

            messages.append(payload)
            slot_index += 1

        return messages

    async def _handle_interrupt(self, stats: Dict[str, Any], start_time: float) -> None:
        """Handle KeyboardInterrupt with support for double Ctrl+C force quit."""
        # Increment interrupt count for double Ctrl+C detection
        current_time = time.time()
        if current_time - self._last_interrupt_time < 2.0:  # Within 2 seconds
            self._interrupt_count += 1
        else:
            self._interrupt_count = 1

        self._last_interrupt_time = current_time

        logger.info("Keyboard interrupt detected", count=self._interrupt_count)
        self._interrupted = True

        # On second interrupt within grace period, force quit
        if self._interrupt_count >= 2:
            logger.error("Double Ctrl+C detected - force quit")
            print("\nForce quit - skipping cleanup")
            sys.exit(1)

        # Graceful shutdown
        await self._shutdown(stats=stats, start_time=start_time)
        raise PublishInterruptError(
            f"Publishing interrupted after {stats.get('sent', 0)} messages"
        )

    async def _shutdown(self, stats: Dict[str, Any], start_time: float) -> None:
        """
        Perform graceful shutdown.

        Writes partial artifacts and cleans up worker pool.

        Args:
            stats: Current publish statistics
            start_time: Start time for duration calculation
        """
        logger.info("Shutting down publisher (interrupted)")

        # Update duration
        stats["duration"] = time.time() - start_time

        # Write partial artifacts
        await self._write_partial_artifacts(stats)

        # Cleanup worker pool with timeout
        try:
            logger.info("Cleaning up worker pool")
            await asyncio.wait_for(self._worker_pool.cleanup(), timeout=5.0)
            logger.info("Cleanup complete")
        except asyncio.TimeoutError:
            logger.error("Worker pool cleanup timed out")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))

    async def _write_partial_artifacts(self, stats: Dict[str, Any]) -> None:
        """
        Write partial artifacts (run.json) on interruption.

        For Phase 2, we'll use a simple JSON format. Full artifact format comes in Phase 4.

        Args:
            stats: Current publish statistics
        """
        if not self.artifact_dir:
            logger.debug("No artifact directory specified - skipping write")
            return

        try:
            # Create artifact directory if needed
            self.artifact_dir.mkdir(parents=True, exist_ok=True)

            # Create run.json with basic stats
            artifact_file = self.artifact_dir / "run.json"

            artifact_data = {
                "status": "interrupted",
                "messages_sent": stats.get("sent", 0),
                "messages_failed": stats.get("failed", 0),
                "duration_seconds": stats.get("duration", 0.0),
                "interrupted_at": time.time(),
            }

            # Write JSON file
            with open(artifact_file, "w") as f:
                json.dump(artifact_data, f, indent=2)

            logger.info(
                f"Partial artifacts written to {artifact_file}", stats=artifact_data
            )

        except Exception as e:
            logger.error("Failed to write partial artifacts", error=str(e))
