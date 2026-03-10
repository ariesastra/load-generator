---
status: testing
phase: 02-publishing-engine
source: [02-00-SUMMARY.md, 02-01-SUMMARY.md, 02-02-SUMMARY.md, 02-03-SUMMARY.md, 02-04-SUMMARY.md, 02-05-SUMMARY.md]
started: 2026-03-10T23:58:00Z
updated: 2026-03-10T23:58:00Z
---

## Current Test
number: 1
name: MQTT Client Connection and Publishing
expected: |
  Create an MQTTClient instance with broker config (host='localhost', port=1883, qos=1).
  Connect to the broker successfully.
  Publish a test message to a topic.
  Disconnect gracefully.
  Verify no errors occur during the lifecycle.
awaiting: user response

## Tests

### 1. MQTT Client Connection and Publishing
expected: Create an MQTTClient instance with broker config (host='localhost', port=1883, qos=1). Connect to the broker successfully. Publish a test message to a topic. Disconnect gracefully. Verify no errors occur during the lifecycle.
result: pending

### 2. MQTT Client QoS Validation
expected: Attempt to create MQTTClient with qos=3. Verify ValueError is raised indicating QoS must be 0, 1, or 2.
result: pending

### 3. MQTT Client TLS Port Auto-Configuration
expected: Create MQTTClient with tls_enabled=True and default port. Verify port is automatically set to 8883. Connection uses TLS correctly.
result: pending

### 4. Worker Pool Concurrent Publishing
expected: Create WorkerPool with worker_count=5. Publish 10 messages concurrently. Verify messages are distributed across workers using round-robin. All workers participate in publishing.
result: pending

### 5. Worker Pool Pre-Connect Fail-Fast
expected: Create WorkerPool with invalid broker config. Call initialize(). Verify that if any worker fails to connect, all already-connected workers are disconnected and WorkerConnectionError is raised.
result: pending

### 6. Rate Limiter Token Bucket Throttling
expected: Create TokenBucketRateLimiter with rate_limit=10. Call acquire() 15 times rapidly. Verify first 10 calls succeed immediately. Next 5 calls block/wait for tokens to refill.
result: pending

### 7. Rate Limiter Burst Capacity
expected: Create TokenBucketRateLimiter with rate_limit=10 and capacity=50. Send 50 messages immediately (burst). All succeed. Send 1 more - it blocks waiting for refill.
result: pending

### 8. Retry Policy Exponential Backoff
expected: Create RetryPolicy with max_retries=3, strategy=EXPONENTIAL, base_delay=0.1, multiplier=2. Simulate a publish that fails 3 times then succeeds. Verify retries happen with delays: 0s, 0.1s, 0.2s (exponential pattern).
result: pending

### 9. Retry Policy Artifact Writing
expected: Create RetryPolicy with artifact_path='failed_events.jsonl'. Run a publish that exhausts all retries and fails. Verify 'failed_events.jsonl' is created with a JSONL line containing: trxId, payload, error, retry_count, timestamp.
result: pending

### 10. Publisher Orchestrator Full Workflow
expected: Create Publisher with broker_config, worker_count=3, message_count=100, rate_limit=50. Call run(). Verify 100 messages are published. Verify statistics returned include: sent, failed, duration (in seconds).
result: pending

### 11. Publisher Graceful Shutdown on Ctrl+C
expected: Start a Publisher run with message_count=10000. Press Ctrl+C during publishing. Verify publishing stops immediately. Verify partial artifacts written to run.json showing messages sent before interruption. Verify graceful MQTT DISCONNECT sent to broker.
result: pending

### 12. Publisher Double Ctrl+C Force Quit
expected: Start a Publisher run. Press Ctrl+C once (graceful shutdown initiates). Press Ctrl+C again within 2 seconds. Verify immediate sys.exit(1) without waiting for cleanup.
result: pending

## Summary

total: 12
passed: 0
issues: 0
pending: 12
skipped: 0

## Gaps

[none yet]
