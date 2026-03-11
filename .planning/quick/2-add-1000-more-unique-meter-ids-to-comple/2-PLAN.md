---
phase: quick
plan: 2
type: execute
wave: 1
depends_on: []
files_modified: [Complete-Asset-Meter.csv]
autonomous: true
requirements: []
user_setup: []

must_haves:
  truths:
    - "Complete-Asset-Meter.csv contains 1000+ additional unique meter IDs"
    - "All new meter IDs are unique (no duplicates within new entries or existing)"
    - "All new entries follow the same CSV structure as existing rows"
    - "All meter IDs are 12 characters (matching existing format)"
  artifacts:
    - path: "Complete-Asset-Meter.csv"
      provides: "Extended meter ID dataset for load testing"
      min_lines: 1035 # header + 34 existing + 1000 new = 1035
  key_links:
    - from: "Complete-Asset-Meter.csv"
      to: "loadgen test scenarios"
      via: "CSV reader in scenarios"
      pattern: "csv.*meter_id"
---

<objective>
Add 1000 more unique meter IDs to Complete-Asset-Meter.csv for load testing capacity.

Purpose: Enable testing with larger meter populations (currently limited to 34 unique IDs)
Output: Extended Complete-Asset-Meter.csv with 1034+ total meter entries (header + existing + 1000 new)
</objective>

<execution_context>
@/Users/ariesastra/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ariesastra/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

## Current State

Complete-Asset-Meter.csv contains:
- Header row + 34 meter entries (35 total lines)
- Meter IDs in column 5 (0-indexed column 4)
- Existing meter ID format: 12 characters, zero-padded numeric (e.g., "000000000013")
- Mix of formats: zero-padded (000000000013) and non-padded (14611837011, 50610000056)

## CSV Structure

All rows share the same 73-column schema with fields:
- warehouse_id, warehouse_name, project_id, hes_id, **meter_id**, meter_manufacture, ...
- meter_id is the critical field for uniqueness
- Other fields can be cloned from existing rows for simplicity
</context>

<tasks>

<task type="auto">
  <name>Task 1: Generate 1000 unique 12-character meter IDs</name>
  <files>Complete-Asset-Meter.csv</files>
  <action>
    Create a Python script that:
    1. Reads existing Complete-Asset-Meter.csv to extract current meter IDs (column 5)
    2. Stores existing IDs in a set for uniqueness check
    3. Generates 1000 new unique 12-character meter IDs using zero-padded format: "{id:012d}"
       - Start from 100000000000 (to avoid conflicts with existing small IDs)
       - Increment sequentially: 100000000000, 100000000001, 100000000002, ...
    4. For each new ID, clone a template row from the CSV (e.g., first data row)
    5. Replace only the meter_id field (column 5) with the new ID
    6. Append all new rows to Complete-Asset-Meter.csv

    Do NOT modify the header or existing 34 rows. Only append new rows.

    Script approach:
    - Use Python csv module (already in use by project)
    - Read existing rows with csv.DictReader
    - Clone first row as template
    - Generate new IDs, update meter_id field
    - Append with csv.DictWriter (mode='a')
  </action>
  <verify>
    <automated>python3 -c "
import csv
with open('Complete-Asset-Meter.csv', 'r') as f:
    reader = csv.reader(f)
    rows = list(reader)
    print(f'Total rows: {len(rows)}')
    meter_ids = [row[4] for row in rows[1:]]  # Skip header
    print(f'Unique meter IDs: {len(set(meter_ids))}')
    print(f'Expected: >= 1034 (header + 34 existing + 1000 new)')
    assert len(rows) >= 1035, f'Expected >=1035 rows, got {len(rows)}'
    assert len(set(meter_ids)) >= 1034, f'Expected >=1034 unique IDs, got {len(set(meter_ids))}'
    print('✓ All checks passed')
"</automated>
  </verify>
  <done>
    Complete-Asset-Meter.csv contains 1035+ lines (header + 34 existing + 1000+ new entries)
    All meter IDs are unique
    New entries follow the same CSV structure as existing rows
  </done>
</task>

</tasks>

<verification>
1. Line count: `wc -l Complete-Asset-Meter.csv` shows >= 1035
2. Unique IDs: Extract meter_id column, confirm >= 1034 unique values
3. CSV validity: File can be read by csv module without errors
4. Data integrity: All new rows have 73 columns matching header
</verification>

<success_criteria>
- Complete-Asset-Meter.csv has 1035+ lines
- Contains 1034+ unique meter IDs (34 original + 1000+ new)
- All new meter IDs are 12 characters, zero-padded
- CSV structure is valid and readable
- No duplicate meter IDs in the file
</success_criteria>

<output>
After completion, create `.planning/quick/2-add-1000-more-unique-meter-ids-to-comple/2-SUMMARY.md`
</output>
