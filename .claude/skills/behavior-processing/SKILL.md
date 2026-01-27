---
name: behavior-processing
description: >-
  Guides AI agents through behavior data processing workflows using this library's MCP server. Provides comprehensive
  documentation of log file formats, hardware module data structures, and processing workflows for Sun Lab VR sessions.
---

# Processing Behavior Data

Guides AI agents through the workflow for processing behavior data from Sun Lab experimental sessions using the
sl-behavior MCP server tools.

---

## Agent Requirements

**You MUST use the MCP tools provided by this library for all behavior data processing tasks.** The sl-behavior library
provides an MCP server that exposes specialized tools for discovering, executing, and monitoring processing jobs. These
tools are the only supported interface for agentic behavior data processing.

### Mandatory Tool Usage

- You MUST NOT import or call sl-behavior Python functions directly (e.g., `from sl_behavior.pipeline import ...`)
- You MUST NOT attempt to run processing by executing Python scripts or CLI commands
- You MUST use the four MCP tools listed in the "Available Tools" section below
- You MUST verify the MCP server is connected before attempting any processing operations

### Why MCP Tools Are Required

The MCP tools provide:

1. **Background processing** - Jobs run in separate threads, allowing parallel session processing
2. **Automatic queuing** - Sessions beyond parallel capacity are queued and started automatically
3. **Status tracking** - Real-time progress monitoring via the ProcessingTracker system
4. **Error isolation** - Failures in one job don't crash the entire pipeline
5. **Resource management** - Automatic CPU core allocation and cleanup

Direct Python calls bypass these capabilities and will fail in agentic contexts.

---

## MCP Server Configuration

The MCP server must be running and connected for the tools to be available.

### Server Startup

The server is started via the CLI:

```bash
sl-behavior mcp
```

### Claude Code Configuration

Add to your `.mcp.json` file in the project root:

```json
{
  "mcpServers": {
    "sl-behavior": {
      "type": "stdio",
      "command": "sl-behavior",
      "args": ["mcp"]
    }
  }
}
```

### Verifying Connection

Before processing, verify the MCP tools are available by checking your tool list. If the four sl-behavior tools
(`list_available_jobs_tool`, `get_processing_status_tool`, `start_processing_tool`, `check_output_files_tool`) are not
present, the server is not connected.

---

## Available Tools

The MCP server exposes four tools. You MUST use these tools for all processing operations.

| Tool                        | Purpose                                                            |
|-----------------------------|--------------------------------------------------------------------|
| `list_available_jobs_tool`  | Discovers which jobs can run based on existing .npz log files      |
| `start_processing_tool`     | Starts processing for one or more sessions (with automatic queuing)|
| `get_processing_status_tool`| Returns status for all sessions being managed                      |
| `check_output_files_tool`   | Verifies .feather output files exist and reports their sizes       |

---

## Tool Input/Output Formats

### `start_processing_tool`

**Input:**
```python
{
    "session_paths": ["/path/to/session1", "/path/to/session2", ...],  # Required, minimum 1
    "process_runtime": True,              # Optional, default True
    "process_face_camera": True,          # Optional, default True
    "process_body_camera": True,          # Optional, default True
    "process_actor_microcontroller": True,   # Optional, default True
    "process_sensor_microcontroller": True,  # Optional, default True
    "process_encoder_microcontroller": True, # Optional, default True
    "workers": -1                         # Optional, -1 for automatic
}
```

**Output:**
```python
{
    "started": True,
    "total_sessions": 30,
    "immediate_start": 1,      # Sessions started immediately
    "queued": 29,              # Sessions waiting in queue
    "max_parallel": 1,         # Max concurrent sessions based on CPU
    "workers_per_session": 28  # CPU cores allocated per session
}
```

### `get_processing_status_tool`

**Input:** None (no parameters required)

**Output:**
```python
{
    "sessions": [
        {
            "session_name": "2024-01-15-10-30-00-123456",
            "status": "PROCESSING",  # PROCESSING, QUEUED, SUCCEEDED, FAILED, PARTIAL
            "completed": 3,          # Completed jobs
            "total": 6,              # Total jobs
            "current_job": "body_camera_processing",
            "job_details": [
                ("runtime_processing", "done"),
                ("face_camera_processing", "done"),
                ("body_camera_processing", "running"),
                ("actor_microcontroller_processing", "pending"),
                ...
            ]
        },
        ...
    ],
    "summary": {
        "total": 30,
        "succeeded": 5,
        "failed": 0,
        "processing": 1,
        "queued": 24
    }
}
```

### `list_available_jobs_tool`

**Input:**
```python
{"session_path": "/path/to/session"}
```

**Output:**
```python
{
    "session_path": "/path/to/session",
    "available": ["runtime_processing", "face_camera_processing", ...],
    "not_available": []
}
```

### `check_output_files_tool`

**Input:**
```python
{"session_path": "/path/to/session"}
```

**Output:**
```python
{
    "output_directory": "/path/to/session/processed_data/behavior_data",
    "file_count": 14,
    "files": [
        {"name": "encoder_data.feather", "size_bytes": 1048576, "size_formatted": "1.0 MB"},
        {"name": "lick_data.feather", "size_bytes": 58777, "size_formatted": "57.4 KB"},
        ...
    ]
}
```

---

## Formatting Status as a Table

When presenting status to the user, format the data as a clear table. Use the summary for overview and sessions list
for details.

**Example formatted output:**

```
Behavior Processing Status
==========================

Summary: 5/30 succeeded | 1 processing | 24 queued | 0 failed

 #  Session                        Status      Progress  Current Job
--- ------------------------------ ----------- --------- ---------------------------
 1  2024-01-15-10-30-00-123456     PROCESSING  3/6 jobs  body_camera_processing
 2  2024-01-15-11-45-00-234567     QUEUED      -         -
 3  2024-01-15-12-00-00-345678     QUEUED      -         -
 4  2024-01-15-13-15-00-456789     QUEUED      -         -
 5  2024-01-15-14-30-00-567890     QUEUED      -         -
...
26  2024-01-16-09-00-00-111111     SUCCEEDED   6/6 jobs  -
27  2024-01-16-10-15-00-222222     SUCCEEDED   6/6 jobs  -
28  2024-01-16-11-30-00-333333     SUCCEEDED   6/6 jobs  -
29  2024-01-16-12-45-00-444444     SUCCEEDED   6/6 jobs  -
30  2024-01-16-14-00-00-555555     SUCCEEDED   6/6 jobs  -
```

**Compact format for many sessions:**

When there are many queued sessions, summarize them:

```
Behavior Processing Status
==========================

Summary: 5/30 succeeded | 1 processing | 24 queued | 0 failed

Active:
  1. 2024-01-15-10-30-00-123456: PROCESSING (3/6 jobs) - body_camera_processing

Queued: 24 sessions waiting

Completed:
  - 2024-01-16-09-00-00-111111: SUCCEEDED (6/6 jobs)
  - 2024-01-16-10-15-00-222222: SUCCEEDED (6/6 jobs)
  - 2024-01-16-11-30-00-333333: SUCCEEDED (6/6 jobs)
  - 2024-01-16-12-45-00-444444: SUCCEEDED (6/6 jobs)
  - 2024-01-16-14-00-00-555555: SUCCEEDED (6/6 jobs)
```

---

## Processing Workflow

The workflow is simple: start processing, then check status when the user asks.

### Workflow Overview

1. **Discover sessions** → Find all session paths to process
2. **Start processing** → Call `start_processing_tool` with all session paths
3. **Inform user** → Report how many started immediately vs queued
4. **Check status on demand** → When user asks, call `get_processing_status_tool` and format as table
5. **Verify outputs** → After completion, optionally verify output files

### Step 1: Discover Sessions

If given a parent directory containing multiple sessions, find all session paths:

```bash
# Find all sessions by looking for session_data.yaml files
find /path/to/data -name "session_data.yaml" -exec dirname {} \;
```

Or use glob patterns to find session directories.

### Step 2: Start Processing

Call `start_processing_tool` with ALL session paths at once:

```
Tool: start_processing_tool
Input: session_paths = ["/path/session1", "/path/session2", ..., "/path/session30"]
```

The tool will:
- Calculate max parallel sessions based on CPU cores
- Start up to max_parallel sessions immediately
- Queue the rest for automatic processing
- Return immediately with confirmation

### Step 3: Inform User

After starting, report the batch status:

> "Started processing 30 sessions. With 32 CPU cores, 1 session runs at a time (28 workers).
> 1 session started immediately, 29 queued. Sessions will process automatically.
> Let me know when you'd like to check status."

### Step 4: Check Status (User-Initiated)

When the user asks for status, call `get_processing_status_tool` (no parameters needed) and format the result as a
table:

```
Tool: get_processing_status_tool
Input: (none)
```

Format the returned data clearly (see "Formatting Status as a Table" above).

### Step 5: Verify Outputs (Optional)

After all sessions complete, verify outputs for any session:

```
Tool: check_output_files_tool
Input: session_path = "/path/to/session"
```

---

## Resource Management

### CPU Core Allocation

The system automatically calculates optimal resource allocation:

- **Workers per session**: `min(cpu_count - 4, 30)` cores
- **Max parallel sessions**: `floor((cpu_count + 15) / 30)`

### Example Allocations

| CPU Cores | Max Parallel | Workers/Session | Behavior                               |
|-----------|--------------|-----------------|----------------------------------------|
| 16        | 1            | 12              | Sequential processing                  |
| 32        | 1            | 28              | Sequential, 28 workers per session     |
| 64        | 2            | 30              | 2 concurrent sessions, 30 workers each |
| 96        | 3            | 30              | 3 concurrent sessions                  |
| 128       | 4            | 30              | 4 concurrent sessions                  |

### Processing 30 Sessions on 32 Cores

With 32 cores:
- Max parallel: `floor((32 + 15) / 30) = 1`
- Workers per session: `min(32 - 4, 30) = 28`

The 30 sessions will process sequentially:
1. Session 1 starts immediately with 28 workers
2. When session 1 completes, session 2 starts automatically
3. Continues until all 30 complete
4. No user intervention needed between sessions

---

## Log File Architecture

This library processes `.npz` log archives generated during Sun Lab VR data acquisition sessions. Each log file has a
unique numeric source ID that identifies its origin.

### Source ID Assignments

| Source ID | Log File       | Generator Library                   | Content                              |
|-----------|----------------|-------------------------------------|--------------------------------------|
| 1         | `1_log.npz`    | sl-experiment (Mesoscope-VR)        | VR system state, runtime, trials     |
| 51        | `51_log.npz`   | ataraxis-video-system               | Face camera frame timestamps         |
| 62        | `62_log.npz`   | ataraxis-video-system               | Body camera frame timestamps         |
| 101       | `101_log.npz`  | ataraxis-communication-interface    | Actor microcontroller modules        |
| 152       | `152_log.npz`  | ataraxis-communication-interface    | Sensor microcontroller modules       |
| 203       | `203_log.npz`  | ataraxis-communication-interface    | Encoder microcontroller modules      |

### Common Message Structure

All log files share a common message envelope format:

```
Byte 0:      source_id (uint8)     - Identifies the logging component
Bytes 1-8:   timestamp (uint64)    - Microseconds elapsed since onset (or 0 for onset message)
Bytes 9+:    payload               - Source-specific data
```

### Onset Timestamp Handling

Each log file contains a special onset message where `timestamp = 0`. The payload of this message contains the absolute
UTC timestamp in microseconds since Unix epoch. All other timestamps are relative to this onset, enabling reconstruction
of absolute timestamps via `absolute_time = onset_us + elapsed_us`.

---

## Runtime Data Log (1_log.npz)

The runtime log captures VR system state, session runtime state, trial guidance, and cue sequences. Generated by the
`_MesoscopeVRSystem` class in sl-experiment.

### Message Codes

| Code | Name                      | Payload Size | Description                                    |
|------|---------------------------|--------------|------------------------------------------------|
| 1    | SYSTEM_STATE              | 2 bytes      | VR system configuration state change           |
| 2    | RUNTIME_STATE             | 2 bytes      | Session runtime stage change                   |
| 3    | REINFORCING_GUIDANCE      | 2 bytes      | Water reward trial guidance mode change        |
| 4    | AVERSIVE_GUIDANCE         | 2 bytes      | Gas puff trial guidance mode change            |
| 5    | DISTANCE_SNAPSHOT         | 9 bytes      | Cumulative distance at cue sequence change     |
| >500 | CUE_SEQUENCE              | Variable     | VR wall cue sequence (uint8 array)             |

### VR System States

| Code | State         | Description                                                |
|------|---------------|------------------------------------------------------------|
| 0    | IDLE          | System paused or not conducting acquisition                |
| 1    | REST          | Rest period: brake engaged, screens off, torque enabled    |
| 2    | RUN           | Run period: brake disengaged, encoder enabled              |
| 3    | LICK_TRAINING | Lick training: wheel locked, animal trains to lick         |
| 4    | RUN_TRAINING  | Run training: wheel unlocked, animal trains to run         |

### Trial Decomposition

Cue sequences are decomposed into individual trials using a greedy longest-match algorithm. Each trial type has a unique
wall cue motif (byte sequence) defined in the experiment configuration. The algorithm:

1. Iterates through the cue sequence from the start
2. Matches the longest possible trial motif at each position
3. Records the trial type index and cumulative distance threshold
4. Continues until the entire sequence is decomposed

### Output Files

| Output File                               | Columns                                        |
|-------------------------------------------|------------------------------------------------|
| `system_state_data.feather`               | `time_us`, `system_state`                      |
| `runtime_state_data.feather`              | `time_us`, `runtime_state`                     |
| `reinforcing_guidance_state_data.feather` | `time_us`, `reinforcing_guidance_state`        |
| `aversive_guidance_state_data.feather`    | `time_us`, `aversive_guidance_state`           |
| `vr_cue_data.feather`                     | `vr_cue`, `traveled_distance_cm`               |
| `vr_trigger_zone_data.feather`            | `trigger_zone_start_cm`, `trigger_zone_end_cm` |
| `trial_data.feather`                      | `trial_type_index`, `traveled_distance_cm`     |

---

## Camera Data Logs (51_log.npz, 62_log.npz)

Camera logs contain frame acquisition timestamps generated by ataraxis-video-system's `VideoSystem` class.

### Message Format

**Regular Frame Message (9 bytes total):**

| Offset  | Size    | Type   | Description                           |
|---------|---------|--------|---------------------------------------|
| 0       | 1 byte  | uint8  | Source ID (51 or 62)                  |
| 1-8     | 8 bytes | uint64 | Microseconds elapsed since onset      |

**Onset Message (17 bytes total):**

| Offset  | Size    | Type   | Description                           |
|---------|---------|--------|---------------------------------------|
| 0       | 1 byte  | uint8  | Source ID                             |
| 1-8     | 8 bytes | uint64 | Zero (indicates onset message)        |
| 9-16    | 8 bytes | int64  | Absolute UTC timestamp (microseconds) |

### Output Files

| Input Log      | Output File                         | Columns         |
|----------------|-------------------------------------|-----------------|
| `51_log.npz`   | `face_camera_timestamps.feather`    | `frame_time_us` |
| `62_log.npz`   | `body_camera_timestamps.feather`    | `frame_time_us` |

---

## Microcontroller Data Logs

Microcontroller logs contain hardware module event data generated by ataraxis-communication-interface. Each
microcontroller manages multiple hardware modules identified by (module_type, module_id) pairs.

### Message Format

| Offset  | Size     | Type   | Description                                    |
|---------|----------|--------|------------------------------------------------|
| 0       | 1 byte   | uint8  | Source ID (101, 152, or 203)                   |
| 1-8     | 8 bytes  | uint64 | Microseconds elapsed since onset               |
| 9       | 1 byte   | uint8  | Protocol code (6=MODULE_DATA, 8=MODULE_STATE)  |
| 10      | 1 byte   | uint8  | Module type                                    |
| 11      | 1 byte   | uint8  | Module instance ID                             |
| 12      | 1 byte   | uint8  | Command code                                   |
| 13      | 1 byte   | uint8  | Event code (51+ for custom data)               |
| 14      | 1 byte   | uint8  | Prototype code (data type, MODULE_DATA only)   |
| 15+     | Variable | varies | Data payload (MODULE_DATA only)                |

### Actor Microcontroller (101_log.npz)

Manages actuator hardware modules that control physical outputs.

| Module Type | Instance | Module Name  | Event Codes                                           |
|-------------|----------|--------------|-------------------------------------------------------|
| 3           | 1        | BrakeModule  | 51 (kEngaged), 52 (kDisengaged)                       |
| 5           | 1        | ValveModule  | 51 (kOpen), 52 (kClosed), 54 (kToneOn), 55 (kToneOff) |
| 5           | 2        | GasPuffValve | 51 (kOpen), 52 (kClosed)                              |
| 7           | 1        | ScreenModule | 51 (kOn), 52 (kOff)                                   |

**Output Files:**

| Output File              | Columns                                              | Description                        |
|--------------------------|------------------------------------------------------|------------------------------------|
| `brake_data.feather`     | `time_us`, `brake_torque_N_cm`                       | Brake engagement torque            |
| `valve_data.feather`     | `time_us`, `dispensed_water_volume_uL`, `tone_state` | Water rewards and tone cues        |
| `gas_puff_data.feather`  | `time_us`, `puff_state`, `cumulative_puff_count`     | Gas puff delivery events           |
| `screen_data.feather`    | `time_us`, `screen_state`                            | VR screen on/off state             |

### Sensor Microcontroller (152_log.npz)

Manages sensor hardware modules that capture animal behavior.

| Module Type | Instance | Module Name   | Event Codes                                      |
|-------------|----------|---------------|--------------------------------------------------|
| 4           | 1        | LickModule    | 51 (kChanged) with 12-bit ADC voltage            |
| 6           | 1        | TorqueModule  | 51 (kCCWTorque), 52 (kCWTorque)                  |
| 1           | 1        | TTLModule     | 51 (kInputOn), 52 (kInputOff) for mesoscope sync |

**Output Files:**

| Output File                    | Columns                                       | Description                 |
|--------------------------------|-----------------------------------------------|-----------------------------|
| `lick_data.feather`            | `time_us`, `voltage_12_bit_adc`, `lick_state` | Lick sensor readings        |
| `torque_data.feather`          | `time_us`, `torque_N_cm`                      | Wheel torque measurements   |
| `mesoscope_frame_data.feather` | `time_us`, `ttl_state`                        | Mesoscope frame sync pulses |

### Encoder Microcontroller (203_log.npz)

Manages the rotary encoder for tracking animal locomotion.

| Module Type | Instance | Module Name    | Event Codes                                     |
|-------------|----------|----------------|-------------------------------------------------|
| 2           | 1        | EncoderModule  | 51 (kRotatedCCW), 52 (kRotatedCW) with float64  |

**Output Files:**

| Output File            | Columns                           | Description                  |
|------------------------|-----------------------------------|------------------------------|
| `encoder_data.feather` | `time_us`, `traveled_distance_cm` | Cumulative distance traveled |

---

## Error Handling

### Common Errors

| Error Message                              | Cause                                  | Resolution                              |
|--------------------------------------------|----------------------------------------|-----------------------------------------|
| "At least one session path is required"    | Empty session_paths list               | Provide at least one session path       |
| "No valid session paths provided"          | All paths invalid or don't exist       | Verify paths exist                      |
| "Processing already in progress"           | Batch already running                  | Wait for current batch to complete      |
| "Session path does not exist"              | Invalid path for output check          | Verify the path exists                  |

### Handling Failures

If processing fails for some sessions (check status shows FAILED or PARTIAL):

1. Note which sessions failed from the status output
2. Wait for the current batch to complete
3. Start a new batch with only the failed sessions
4. Check the processing tracker YAML files for detailed error information

---

## Hardware Configuration Dependencies

Processing depends on hardware calibration values stored in `hardware_state.yaml`:

| Parameter                     | Used By             | Description                              |
|-------------------------------|---------------------|------------------------------------------|
| `cm_per_pulse`                | Encoder processing  | Converts encoder pulses to distance (cm) |
| `lick_threshold`              | Lick processing     | ADC threshold for lick detection         |
| `torque_per_adc_unit`         | Torque processing   | Converts ADC to torque (N·cm)            |
| `valve_scale_coefficient`     | Valve processing    | Power law coefficient for water volume   |
| `valve_nonlinearity_exponent` | Valve processing    | Power law exponent for water volume      |
| `minimum_brake_strength`      | Brake processing    | Minimum brake torque (N·cm)              |
| `maximum_brake_strength`      | Brake processing    | Maximum brake torque (N·cm)              |
| `screens_initially_on`        | Screen processing   | Initial screen state at startup          |
| `recorded_mesoscope_ttl`      | TTL processing      | Whether mesoscope sync was recorded      |
| `delivered_gas_puffs`         | Gas puff processing | Whether gas puffs were delivered         |

Missing calibration values cause the corresponding module to be skipped during processing.
