# Phase 1: Input Foundation - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

## Phase Boundary

Load real meter IDs from CSV and generate unique LP periodic payloads with guaranteed uniqueness constraints. This phase builds INPUT-01 through INPUT-04: CSV loader, payload factory, uniqueness guarantees, and slot planner.

## Implementation Decisions

### CSV Format
- Use existing Asset-Meter.csv format with `meter_id` column (15-char zero-padded IDs like "000000000049")
- Basic validation: non-empty values, 15-char format, strip whitespace
- Silent deduplication: remove duplicates silently, log count of duplicates removed
- Silent skip: skip rows with invalid/missing `meter_id` without error
- CSV file path specified via YAML scenario config file

### Payload Schema
- Follow python-mqtt-benchmark.md spec exactly for LP periodic envelope
- Required fields: `trxId`, `meterId`, `dcuId`, `operationType = meterLoadProfilePeriodic`, `operationResult` with LP fields
- `trxId`: UUID v4 format (using `uuid.uuid4()`)
- `dcuId`: Fixed value for all messages (single DCU scenario)
- `operationResult`: Full LP data with register values (power, voltage, current, etc.)
- `samplingTime`: ISO 8601 format (e.g., `2026-03-09T14:00:00Z`)
- `collectionTime`: `samplingTime + delta` (also ISO 8601)

### Uniqueness Strategy
- Track `(meterId, samplingTime)` pairs in in-memory set during generation
- On collision: increment `samplingTime` by 15 minutes until unique
- Uniqueness scope: per-run only (not across ladder sessions)
- Collision handling: log warning and continue with corrected timestamp

### Slot Planner Logic
- Base time: current time, rounded down to nearest 15-minute boundary (:00, :15, :30, :45)
- Slot distribution: sequential per meter (all slots to meter1, then meter2, etc.)
- Timestamp format: ISO 8601 (e.g., `2026-03-09T14:00:00Z`)
- No slot overflow handling needed (won't exceed 96 slots with unique pairs in this phase)

## Specific Ideas

- "I have Asset-Meter.csv in the root at this project" — use existing production CSV format
- Sequential slot distribution prioritizes meter-level grouping before time distribution

## Existing Code Insights

### Reusable Assets
- None — greenfield project

### Established Patterns
- None — first phase

### Integration Points
- None — foundational phase

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 01-input-foundation*
*Context gathered: 2026-03-09*
