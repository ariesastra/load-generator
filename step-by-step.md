# Step-by-Step Testing Guide for Publisher Graceful Shutdown

## Prerequisites

```bash
# Install mosquitto MQTT broker if not already installed
brew install mosquitto  # macOS
# or
sudo apt-get install mosquitto  # Ubuntu/Debian

# Start MQTT broker in verbose mode (in separate terminal)
mosquitto -v
```

## Test 1: Basic Graceful Shutdown

Create a test script `test_shutdown.py`:

```python
import asyncio
from loadgen.publisher import Publisher

async def test_graceful_shutdown():
    pub = Publisher(
        broker_config={'host': 'localhost', 'port': 1883},
        worker_count=2,
        message_count=1000,  # Large enough to allow time for Ctrl+C
        rate_limit=10,  # Slow rate to give you time to interrupt
        artifact_dir='./test_artifacts'
    )

    try:
        stats = await pub.run()
        print(f'Completed: {stats["sent"]} sent, {stats["failed"]} failed')
    except KeyboardInterrupt:
        print('Test interrupted - checking artifacts...')

if __name__ == '__main__':
    asyncio.run(test_graceful_shutdown())
```

**Steps:**
1. **Run the script**: `python3 test_shutdown.py`
2. **Wait 2-3 seconds** for publishing to start
3. **Press Ctrl+C** once
4. **Expected behavior**:
   ```
   [INFO] Starting publishing: 1000 messages, 2 workers, 10 msg/sec
   [INFO] Message 1 sent
   [INFO] Message 2 sent...
   ^C
   [INFO] Shutdown requested (Ctrl+C)
   [INFO] Waiting for in-flight messages to complete...
   [INFO] Writing partial artifacts...
   [INFO] Graceful disconnect from MQTT broker
   [INFO] Shutdown complete (sent: 15, failed: 0)
   ```

5. **Verify artifact created**:
   ```bash
   cat ./test_artifacts/run.json
   ```
   Should show:
   ```json
   {
     "status": "interrupted",
     "messages_sent": 15,
     "messages_failed": 0,
     "duration_seconds": 2.3,
     "interrupted_at": "2026-03-10T10:30:00"
   }
   ```

6. **Verify MQTT DISCONNECT**: Check mosquitto terminal output for:
   ```
   Client <client-id> disconnected (32109).
   ```

## Test 2: Double Ctrl+C Force Quit

**Steps:**
1. Run the test script again: `python3 test_shutdown.py`
2. Wait 1-2 seconds for publishing to start
3. **Press Ctrl+C twice quickly** (within 1-2 seconds)
4. **Expected behavior**:
   ```
   [INFO] Starting publishing...
   ^C
   [INFO] Shutdown requested (Ctrl+C)
   ^C
   [WARNING] Force quit requested - exiting immediately
   ```
   Process exits immediately without cleanup

## Test 3: Verify No Message Loss on Single Ctrl+C

**Steps:**
1. Monitor MQTT messages using:
   ```bash
   mosquitto_sub -h localhost -p 1883 -t 'loadgen/#' -v
   ```

2. Run the test script: `python3 test_shutdown.py`

3. Press Ctrl+C after seeing ~20 messages in the subscriber

4. Check:
   - All messages before Ctrl+C appear in subscriber
   - No duplicate messages
   - run.json count matches subscriber message count

## Test 4: Verify Worker Pool Cleanup

**Steps:**
1. Run test script with verbose logging:
   ```bash
   python3 test_shutdown.py -v  # If you add logging configuration
   ```

2. Press Ctrl+C after 3-4 seconds

3. Verify in logs:
   ```
   [DEBUG] Worker 0: Disconnecting...
   [DEBUG] Worker 1: Disconnecting...
   [DEBUG] All workers cleaned up successfully
   ```

## Test 5: Check Broker Connection State

**Steps:**
1. In separate terminal, monitor connections:
   ```bash
   netstat -an | grep 1883  # Check established connections
   ```

2. Before running: Should show no connections to 1883

3. During test: Should show 2-3 ESTABLISHED connections

4. After graceful shutdown: Should show connections in TIME_WAIT or closed

## Troubleshooting

**If shutdown doesn't work:**
```bash
# Add debug prints to see if signal is being caught
# Edit publisher.py and add:
print("DEBUG: Ctrl+C caught, _interrupted =", self._interrupted)
```

**If artifacts not written:**
```bash
# Check permissions
ls -la ./test_artifacts/

# Ensure directory exists
mkdir -p ./test_artifacts
```

**If MQTT broker shows errors:**
```bash
# Use clean broker instance
pkill mosquitto
mosquitto -v -c /dev/null  # Start with empty config
```

## Success Criteria Checklist

After testing, verify:
- [ ] Single Ctrl+C stops new messages immediately
- [ ] In-flight messages complete before shutdown
- [ ] run.json created with accurate sent/failed counts
- [ ] MQTT DISCONNECT packet sent (visible in mosquitto logs)
- [ ] No duplicate messages on reconnection
- [ ] Double Ctrl+C force quits immediately
- [ ] Process exits cleanly (no hanging)
