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
- You MUST use the three MCP tools listed in the "Available Tools" section below
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

Before processing, verify the MCP tools are available by checking your tool list. If the sl-behavior tools
(`discover_sessions_tool`, `start_processing_tool`, `get_processing_status_tool`) are not present, the server is not
connected.

---

## Available Tools

The MCP server exposes three tools. You MUST use these tools for all processing operations.

| Tool                         | Purpose                                                             |
|------------------------------|---------------------------------------------------------------------|
| `discover_sessions_tool`     | Finds sessions under a root directory, returns session root paths   |
| `start_processing_tool`      | Starts processing for one or more sessions (with automatic queuing) |
| `get_processing_status_tool` | Returns status for all sessions being managed                       |

---

## Tool Input/Output Formats

### `discover_sessions_tool`

**Input:**
```python
{
    "root_directory": "/path/to/data"  # Required, directory to search
}
```

**Output:**
```python
{
    "sessions": [
        "/path/to/data/animal1/2024-01-15-10-30-00-123456",
        "/path/to/data/animal1/2024-01-16-09-00-00-234567",
        ...
    ],
    "count": 30
}
```

The tool searches for `session_data.yaml` files recursively and returns the resolved session root paths (parent of
`raw_data`). These paths can be passed directly to `start_processing_tool`.

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
            ],
            "errors": [              # Only present if status is FAILED or PARTIAL
                "actor_microcontroller_processing: KeyError: 'cm_per_pulse' (pipeline.py:234)"
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

---

## Formatting Status as a Table

When presenting status to the user, you MUST format the data as a clear table. The table MUST include these three
columns for each session:

1. **Full Session Name** - The complete session identifier (e.g., `2024-01-15-10-30-00-123456`)
2. **Job Completion State** - Progress as `completed/total` jobs (e.g., `3/6`)
3. **Currently Executing Job** - The job currently running, or `-` if queued/completed

**Required table format:**

```
| Session                      | Completion | Current Job              |
|------------------------------|------------|--------------------------|
| 2024-01-15-10-30-00-123456   | 3/6        | body_camera_processing   |
| 2024-01-15-11-45-00-234567   | 0/6        | (queued)                 |
| 2024-01-16-09-00-00-111111   | 6/6        | -                        |
```

**Full example with summary:**

```
**Processing Status Check**

Summary: 5/30 succeeded | 1 processing | 24 queued | 0 failed

| Session                      | Completion | Current Job              |
|------------------------------|------------|--------------------------|
| 2024-01-15-10-30-00-123456   | 3/6        | body_camera_processing   |
| 2024-01-15-11-45-00-234567   | 0/6        | (queued)                 |
| 2024-01-15-12-00-00-345678   | 0/6        | (queued)                 |
| 2024-01-16-09-00-00-111111   | 6/6        | -                        |
| 2024-01-16-10-15-00-222222   | 6/6        | -                        |
```

**Important:** Always use the FULL session name from the session path, not a truncated version. The session name is
typically found in the path (e.g., `/home/data/test_run/2024-01-15-10-30-00-123456/raw_data` -> session name is
`2024-01-15-10-30-00-123456`).

---

## Processing Workflow

The workflow starts processing in the background and allows the user to check status on demand.

### Pre-Processing Checklist

**You MUST complete this checklist before calling `start_processing_tool`.** Do not skip any step.

```
- [ ] Session discovery complete (used discover_sessions_tool or received explicit paths)
- [ ] Asked user about CPU core allocation (see Step 2 below)
- [ ] Received user response confirming worker count (number or "all"/automatic)
- [ ] Confirmed which job types to process (if user has specific requirements)
```

**STOP**: If any checkbox is incomplete, do not proceed to `start_processing_tool`. Complete the missing steps first.

### Workflow Overview

1. **Discover sessions** → Find all session paths to process
2. **Ask about CPU allocation** → Explain resource model and ask how many cores to use
3. **Start processing** → Call `start_processing_tool` with session paths and worker count
4. **Inform user** → Report batch status and explain how to check progress
5. **Check status on request** → When the user asks, display status table
6. **Explain any errors** → When processing completes with failures, analyze and explain errors

### Step 1: Discover Sessions

If given a parent directory containing multiple sessions, use the `discover_sessions_tool` to find all session paths:

```
Tool: discover_sessions_tool
Input: root_directory = "/path/to/data"
```

The tool searches for `session_data.yaml` files and returns the resolved session root paths.

### Step 2: Ask About CPU Allocation

Before starting processing, you MUST ask the user how many CPU cores to dedicate. Explain the resource allocation
model so they can make an informed decision:

> "Found [N] sessions to process. Before starting, how many CPU cores should I dedicate to processing?
>
> **Resource allocation model:**
> - Each session saturates at **30 cores** (using more provides no benefit)
> - To process **2+ sessions in parallel**, you need at least **45 cores** (30 for the first + 15 minimum for each
>   additional session)
> - The system reserves 4 cores for overhead, so available workers = total cores - 4
>
> Your system has [X] cores. With all cores dedicated, [Y] session(s) can process in parallel.
> You can specify fewer cores if you want to leave resources for other work.
>
> How many cores would you like to use? (Enter a number, or 'all' for automatic allocation)"

**After the user responds:**
- If they say "all" or want automatic allocation, use `workers: -1`
- If they specify a number, use that as the `workers` parameter
- If they specify fewer than 12 cores, warn that processing will be slow but proceed if they confirm

### Step 3: Start Processing

Call `start_processing_tool` with ALL session paths and the worker count:

```
Tool: start_processing_tool
Input: session_paths = ["/path/session1", "/path/session2", ..., "/path/session30"]
       workers = -1  # or the user-specified number
```

The tool will:
- Calculate max parallel sessions based on allocated cores
- Start up to max_parallel sessions immediately
- Queue the rest for automatic processing
- Return immediately with confirmation

### Step 4: Inform User

After starting, report the batch status and explain that processing runs in the background:

> "Started processing [N] sessions with [X] workers per session. [Y] session(s) processing in parallel,
> [Z] queued.
>
> Processing runs in the background. You can ask me to check status at any time, or request periodic updates
> (e.g., 'check every 5 minutes'). I'll display a progress table whenever you ask."

### Step 5: Check Status on Request

When the user requests a status update, call `get_processing_status_tool` and display the formatted table:

```
Tool: get_processing_status_tool
Input: (none)
```

**If the user requests periodic updates** (e.g., "check every 10 minutes"), honor that request and check at the
specified interval until processing completes.

**When processing completes** (`processing: 0` and `queued: 0`), proceed to Step 6 for error analysis.

### Step 6: Explain Any Errors

**You MUST analyze and explain any errors when processing completes.** This is a mandatory step, not optional.

When the status check shows sessions with FAILED or PARTIAL status:

1. **Read the LOG_ARCHITECTURE.md reference** to understand log file structures and common error patterns
2. **Extract error messages** from the status output's `errors` field for each failed session
3. **Identify the root cause** by mapping the error to the appropriate section in LOG_ARCHITECTURE.md
4. **Explain to the user** in plain language what went wrong and how to fix it

**Error explanation format:**

```
**Processing Complete**

Summary: 28/30 succeeded | 0 processing | 0 queued | 2 failed

**Failed Sessions:**

1. **2024-01-15-10-30-00-123456** - FAILED
   - Error: `actor_microcontroller_processing: KeyError: 'minimum_brake_strength' (pipeline.py:234)`
   - Cause: The `hardware_state.yaml` file is missing the brake calibration value required to process
     brake engagement data from the Actor microcontroller (101_log.npz).
   - Fix: Add `minimum_brake_strength` and `maximum_brake_strength` to the session's `hardware_state.yaml`.

2. **2024-01-16-09-00-00-234567** - PARTIAL
   - Error: `encoder_microcontroller_processing: FileNotFoundError: 203_log.npz`
   - Cause: The encoder log file is missing. This can occur if the encoder microcontroller was not
     enabled during the session or if the log file was not transferred correctly.
   - Fix: Verify the encoder was enabled in the experiment configuration. If it was, check if
     `203_log.npz` exists in the session's `raw_data/` directory.
```

**If all sessions succeed**, simply report completion:

```
**Processing Complete**

Summary: 30/30 succeeded | 0 processing | 0 queued | 0 failed

All sessions processed successfully. Output files are ready in each session's `behavior_data/` directory.
```

---

## Log File Reference

For detailed information about log file formats, message structures, and hardware module data, refer to
[LOG_ARCHITECTURE.md](LOG_ARCHITECTURE.md).

Use this reference when:
- Answering user questions about log composition or data structures
- Debugging processing errors
- Understanding which log files map to which processing jobs
- Identifying missing calibration values in hardware_state.yaml

### Quick Reference: Jobs to Log Files

| Processing Job                       | Input Log File | Source ID |
|--------------------------------------|----------------|-----------|
| `runtime_processing`                 | `1_log.npz`    | 1         |
| `face_camera_processing`             | `51_log.npz`   | 51        |
| `body_camera_processing`             | `62_log.npz`   | 62        |
| `actor_microcontroller_processing`   | `101_log.npz`  | 101       |
| `sensor_microcontroller_processing`  | `152_log.npz`  | 152       |
| `encoder_microcontroller_processing` | `203_log.npz`  | 203       |

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

## Error Handling

### Common Errors

| Error Message                              | Cause                                  | Resolution                              |
|--------------------------------------------|----------------------------------------|-----------------------------------------|
| "At least one session path is required"    | Empty session_paths list               | Provide at least one session path       |
| "No valid session paths provided"          | All paths invalid or don't exist       | Verify paths exist                      |
| "Processing already in progress"           | Batch already running                  | Wait for current batch to complete      |
| "Session path does not exist"              | Invalid path for output check          | Verify the path exists                  |

### Handling Failures

If processing fails for some sessions (status shows FAILED or PARTIAL):

1. Note which sessions failed from the status output
2. **Read the error messages** in the `errors` field
3. **Consult LOG_ARCHITECTURE.md** to understand the data structures involved
4. **Explain the errors** to the user with root cause and resolution
5. Wait for the current batch to complete before starting any retries
