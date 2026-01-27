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
2. **Status tracking** - Real-time progress monitoring via the ProcessingTracker system
3. **Error isolation** - Failures in one job don't crash the entire pipeline
4. **Resource management** - Automatic CPU core allocation and cleanup

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
(`list_available_jobs_tool`, `get_processing_status_tool`, `start_processing_tool`, `check_output_files_tool`) are
not present, the server is not connected.

---

## Available Tools

The MCP server exposes exactly four tools. You MUST use these tools for all processing operations.

| Tool                         | Purpose                                                       |
|------------------------------|---------------------------------------------------------------|
| `list_available_jobs_tool`   | Discovers which jobs can run based on existing .npz log files |
| `get_processing_status_tool` | Checks processing state (PROCESSING, SUCCEEDED, FAILED, etc.) |
| `start_processing_tool`      | Starts processing in background thread, returns immediately   |
| `check_output_files_tool`    | Verifies .feather output files exist and reports their sizes  |

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

## Processing Workflow

### Step 1: Discover Available Jobs

Before starting processing, check which jobs are available for the session:

```
Tool: list_available_jobs_tool
Input: session_path = "/path/to/session"
```

Returns which log files exist and which jobs can run.

### Step 2: Start Processing

Start processing in the background. The tool returns immediately, allowing parallel session processing:

```
Tool: start_processing_tool
Input:
  session_path = "/path/to/session"
  process_runtime = true
  process_face_camera = true
  process_body_camera = true
  process_actor_microcontroller = true
  process_sensor_microcontroller = true
  process_encoder_microcontroller = true
  workers = -1
```

Setting `workers = -1` uses all available CPU cores. Set to `1` for sequential processing.

### Step 3: Monitor Progress

Check processing status periodically:

```
Tool: get_processing_status_tool
Input: session_path = "/path/to/session"
```

Status values:

| Status        | Meaning                                             |
|---------------|-----------------------------------------------------|
| `PROCESSING`  | Background thread is actively processing            |
| `SUCCEEDED`   | All jobs completed successfully                     |
| `FAILED`      | One or more jobs failed                             |
| `PARTIAL`     | Some jobs succeeded, some failed                    |
| `PENDING`     | Jobs are queued but not yet started                 |
| `NOT_STARTED` | No tracker file exists (processing never initiated) |

### Step 4: Verify Outputs

After processing completes, verify the output files:

```
Tool: check_output_files_tool
Input: session_path = "/path/to/session"
```

Lists all `.feather` files in the processed data directory with their sizes.

---

## Resource Management

### CPU Core Allocation

Each session processing job uses a **maximum of 30 CPU cores** when `workers = -1` is specified. This limit ensures
efficient resource utilization without overwhelming the system.

### Checking Available Cores

Before starting processing, you MUST check the machine's CPU count to determine optimal parallelization:

```bash
# Check CPU count on Linux/macOS
nproc  # or: python -c "import os; print(os.cpu_count())"
```

### Calculating Parallel Session Capacity

Prefer fully saturating sessions (30 cores each) over running multiple partially-saturated sessions. Use 15 cores
(half maximum capacity) as the minimum threshold for spawning an additional session:

```
max_parallel_sessions = floor((cpu_count + 15) / 30)
```

| CPU Cores | Max Parallel Sessions | Core Distribution                           |
|-----------|-----------------------|---------------------------------------------|
| < 30      | 1                     | Single session, partial core usage          |
| 30-44     | 1                     | Single session fully saturated              |
| 45-59     | 2                     | One full (30) + one partial (15-29) session |
| 60-74     | 2                     | Two fully saturated sessions                |
| 75-89     | 3                     | Two full + one partial session              |
| 90-104    | 3                     | Three fully saturated sessions              |
| 105-119   | 4                     | Three full + one partial session            |
| 120+      | 4+                    | Continues pattern                           |

### When to Spawn Multiple Sessions

You SHOULD spawn multiple session processing instances when:

1. **Sufficient cores available**: `cpu_count >= 45` allows 2+ parallel sessions
2. **Multiple sessions to process**: You have a batch of sessions waiting
3. **No other CPU-intensive tasks**: The machine is not running other heavy workloads

You SHOULD NOT spawn multiple sessions when:

1. **Limited cores**: `cpu_count < 45` means the second session would be severely under-resourced
2. **Memory constraints**: Each session requires ~4-8 GB RAM for large datasets
3. **Disk I/O bottleneck**: Slow storage limits parallel processing benefit

---

## Parallel Processing

The MCP server supports processing multiple sessions in parallel. Each session runs in its own background thread.

### Starting Multiple Sessions

You can start processing for multiple sessions without waiting for each to complete:

```
1. start_processing_tool(session_path="/data/session_A") -> "Processing started..."
2. start_processing_tool(session_path="/data/session_B") -> "Processing started..."
3. start_processing_tool(session_path="/data/session_C") -> "Processing started..."
```

### Monitoring Multiple Sessions

Check status for each session independently:

```
get_processing_status_tool(session_path="/data/session_A") -> "Status: PROCESSING..."
get_processing_status_tool(session_path="/data/session_B") -> "Status: SUCCEEDED..."
get_processing_status_tool(session_path="/data/session_C") -> "Status: PROCESSING..."
```

### Best Practices for Parallel Processing

You MUST follow these practices when processing multiple sessions:

1. Start all sessions before checking any status to maximize parallelism.
2. Poll status at reasonable intervals (every 30-60 seconds for large sessions).
3. Continue with other tasks while processing runs in the background.
4. Verify outputs for all sessions after all processing completes.

---

## Background Monitoring with Task Agents

When processing multiple sessions, you SHOULD use a background Task agent to monitor progress and provide formatted
status updates to the user.

### Spawning a Background Monitor Agent

Use the Task tool with `run_in_background: true` to spawn a monitoring agent:

```
Tool: Task
Input:
  subagent_type: "general-purpose"
  run_in_background: true
  prompt: "Monitor behavior processing status for sessions [list paths]. Poll every 30 seconds and format results."
  description: "Monitor processing status"
```

### Status Formatting Requirements

The background monitoring agent MUST format status data as a human-readable table before displaying to the user. Raw
status output is difficult to parse at a glance.

**Required table format:**

```
+----------------------------------------------------------------------------+
|                    Behavior Processing Status                              |
+--------------------------+------------+----------+-------------------------+
| Session                  | Status     | Progress | Details                 |
+--------------------------+------------+----------+-------------------------+
| /data/2024-01-15_mouse1  | PROCESSING | 4/6 jobs | Processing encoder...   |
| /data/2024-01-15_mouse2  | SUCCEEDED  | 6/6 jobs | Complete                |
| /data/2024-01-15_mouse3  | FAILED     | 3/6 jobs | Lick processing failed  |
| /data/2024-01-15_mouse4  | PENDING    | 0/6 jobs | Queued                  |
+--------------------------+------------+----------+-------------------------+
Last updated: 2024-01-15 14:32:15
```

### Formatting Guidelines

1. **Session column**: Show shortened path (last 2-3 components) for readability
2. **Status column**: Use exact status values (PROCESSING, SUCCEEDED, FAILED, PARTIAL, PENDING, NOT_STARTED)
3. **Progress column**: Show completed jobs vs total jobs (e.g., "4/6 jobs")
4. **Details column**: Show current operation for PROCESSING, error summary for FAILED
5. **Timestamp**: Always include last update time at the bottom

### Example Background Monitor Implementation

The background agent should follow this workflow:

```
1. Initialize session list and status tracking
2. Loop until all sessions complete:
   a. Call get_processing_status_tool for each session
   b. Parse status responses
   c. Format as table
   d. Output formatted table to background preview
   e. Sleep 30 seconds
3. Output final summary when all sessions complete
```

### Reading Background Agent Output

Check the background agent's progress using the Read tool on its output file:

```bash
# The Task tool returns an output_file path when run_in_background is true
# Use Read or tail to view the current status
```

---

## Error Handling

### Common Errors

| Error Message                    | Cause                                  | Resolution                              |
|----------------------------------|----------------------------------------|-----------------------------------------|
| "Session path does not exist"    | Invalid or mistyped session path       | Verify the path exists                  |
| "Processing already in progress" | Session is already being processed     | Wait for current processing to complete |
| "No output directory found"      | Session has not been processed yet     | Run processing first                    |
| "No .feather files found"        | Processing failed or has not completed | Check processing status for errors      |

### Handling Failures

If processing fails (status = FAILED or PARTIAL):

1. Check the processing tracker file for detailed error information.
2. Verify input .npz files are not corrupted.
3. Ensure sufficient disk space for output files.
4. Re-run processing for failed jobs only by setting other job flags to `false`.

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
