# Basic Graceful Shutdown Test - Implementation Guide

## Overview

This guide walks you through implementing and testing the graceful shutdown feature using `test_shutdown.py`.

## Prerequisites Check

### 1. Install MQTT Broker (if not already installed)

```bash
# macOS
brew install mosquitto

# Ubuntu/Debian
sudo apt-get install mosquitto

# Verify installation
mosquitto -h
```

### 2. Verify Python Environment

```bash
# Check Python version (3.8+)
python3 --version

# Install loadgen package in development mode
pip install -e .
```

### 3. Verify Dependencies

```bash
# Check required packages are installed
pip list | grep -E "paho|structlog"
```

## Test Execution Steps

### Step 1: Start MQTT Broker

Open **Terminal 1** and start the broker with verbose output:

```bash
mosquitto -v
```

**Expected output:**
```
1615372800: mosquitto version 2.x.x starting
1615372800: Using default config file /usr/local/etc/mosquitto/mosquitto.conf
1615372800: Opening socket on port 1883.
```

**Keep this terminal open** - it shows broker activity and will confirm when clients connect/disconnect.

### Step 2: Run the Test Script

Open **Terminal 2** in the project root and run:

```bash
python3 test_shutdown.py
```

**Expected initial output:**
```
[INFO] Starting graceful shutdown test...
[INFO] Press Ctrl+C after 2-3 seconds to trigger shutdown
[INFO] Watch for:
  - Immediate stop of new message sends
  - Completion of in-flight messages
  - Artifact file creation

[INFO] Starting publishing: 1000 messages, 2 workers, 10 msg/sec
[INFO] Message 1 sent
[INFO] Message 2 sent
[INFO] Message 3 sent
...
```

### Step 3: Trigger Graceful Shutdown

**After 2-3 seconds** of messages being published:

```bash
Press Ctrl+C once
```

You should see (in Terminal 2):

```
[INFO] Shutdown requested (Ctrl+C)
[INFO] Waiting for in-flight messages to complete...
[INFO] Writing partial artifacts...
[INFO] Graceful disconnect from MQTT broker
[INFO] Shutdown complete (sent: 15, failed: 0)

[INFO] Test interrupted - checking artifacts...
[INFO] ✓ Artifact created at ./test_artifacts/run.json
[INFO] Status: interrupted
[INFO] Messages sent: 15
[INFO] Messages failed: 0
[INFO] Duration: 2.3s
```

### Step 4: Verify MQTT Broker Output

Check **Terminal 1** (where mosquitto is running) for:

```
[timestamp] New connection from <IP address> port 12345.
[timestamp] New client connected from <IP address> as auto-XXXXX.
...
[timestamp] Client auto-XXXXX disconnected (32109).
```

This confirms the MQTT DISCONNECT packet was sent.

### Step 5: Verify Artifacts

In **Terminal 2**, verify the artifact file was created:

```bash
cat test_artifacts/run.json
```

**Expected content:**
```json
{
  "status": "interrupted",
  "messages_sent": 15,
  "messages_failed": 0,
  "duration_seconds": 2.3,
  "interrupted_at": "2026-03-10T10:30:00"
}
```

## Success Criteria

✅ **Graceful shutdown is working if:**
- [ ] Single Ctrl+C stops new message publishing immediately
- [ ] In-flight messages (already sent) complete normally
- [ ] run.json is created with `"status": "interrupted"`
- [ ] Message count in artifact matches observed output
- [ ] MQTT broker shows clean DISCONNECT (code 32109)
- [ ] Process exits cleanly without hanging
- [ ] No duplicate messages after shutdown

## Troubleshooting

### Issue: "Connection refused" Error

```
[ERROR] ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:**
```bash
# Verify mosquitto is running
lsof -i :1883

# If not running, start it:
mosquitto -v

# Or check if it's running as a service:
brew services list | grep mosquitto
```

### Issue: Artifacts Directory Not Created

```bash
# Create manually:
mkdir -p test_artifacts

# Verify permissions:
ls -la test_artifacts/
```

### Issue: Script Hangs After Shutdown

This might indicate the worker pool isn't cleaning up properly.

```bash
# Force quit with:
Ctrl+C Ctrl+C  (press twice quickly)

# Check for hanging processes:
ps aux | grep python
```

### Issue: No Messages Being Published

Check the broker isn't blocking connections:

```bash
# In Terminal 1, watch for connection errors:
mosquitto -v

# Check if firewall is blocking port 1883:
netstat -an | grep 1883
```

## Advanced: Monitor MQTT Traffic

In **Terminal 3**, subscribe to all messages to verify they're being sent:

```bash
mosquitto_sub -h localhost -p 1883 -t 'loadgen/#' -v
```

You should see:
```
loadgen/payload_0 {"type": "temperature", "value": 23.5, ...}
loadgen/payload_1 {"type": "temperature", "value": 24.1, ...}
...
```

## Advanced: Test Double Ctrl+C (Force Quit)

After running the test once, you can test force quit:

```bash
# Run again:
python3 test_shutdown.py

# Wait a few seconds, then:
Ctrl+C  # First interrupt (graceful)
Ctrl+C  # Second interrupt (force quit) - within 1-2 seconds

# Expected output:
# [WARNING] Force quit requested - exiting immediately
```

## Next Steps

After successful basic graceful shutdown test, you can:

1. **Test 2:** Double Ctrl+C force quit (see step-by-step.md)
2. **Test 3:** Message loss verification with mqtt subscriber
3. **Test 4:** Worker pool cleanup verification with logging
4. **Test 5:** Broker connection state monitoring

See [step-by-step.md](./step-by-step.md) for all test scenarios.

## Cleanup

After testing, clean up artifacts:

```bash
rm -rf test_artifacts/
rm test_shutdown.py  # Optional - keep for future testing
```
