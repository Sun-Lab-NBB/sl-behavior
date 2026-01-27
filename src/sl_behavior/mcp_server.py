"""Provides the MCP server for agentic behavior data processing.

Exposes tools that enable AI agents to discover available processing jobs, start processing in the background, monitor
processing status, and verify output files.
"""

from __future__ import annotations

from os import cpu_count
from typing import Literal
from pathlib import Path
from threading import Thread

from sl_shared_assets import SessionData, ProcessingStatus, ProcessingTracker, ProcessingTrackers
from mcp.server.fastmcp import FastMCP

from .pipeline import (
    BehaviorJobNames,
    _execute_job,
    _resolve_available_jobs,
    _initialize_processing_tracker,
)

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sl-behavior", json_response=True)

# Module-level state for tracking active processing sessions.
_active_sessions: dict[str, Thread] = {}

# Bytes per kilobyte, used for file size formatting.
_BYTES_PER_KB: int = 1024

# CPU cores reserved for system operations.
_RESERVED_CORES: int = 4

# Maximum CPU cores any single job can use.
_MAXIMUM_JOB_CORES: int = 30


def _calculate_job_workers(requested_workers: int) -> int:
    """Calculates the number of CPU cores to allocate for a processing job.

    Determines available cores based on system CPU count minus reserved cores, capped at the maximum limit.
    This ensures each job receives substantial resources while leaving headroom for system operations
    and allowing multiple sessions to process in parallel.

    Args:
        requested_workers: The user-requested worker count. Set to -1 or less to use the calculated default.

    Returns:
        The number of CPU cores to use for the job.
    """
    if requested_workers > 0:
        return min(requested_workers, _MAXIMUM_JOB_CORES)

    available_cores = cpu_count()
    if available_cores is None:
        return _RESERVED_CORES  # Fallback if cpu_count() returns None.

    return min(max(1, available_cores - _RESERVED_CORES), _MAXIMUM_JOB_CORES)


def _execute_single_job(
    session_path: Path,
    base_job_name: str,
    session_name: str,
    job_id: str,
    workers: int,
    tracker: ProcessingTracker,
) -> tuple[str, bool, str | None]:
    """Executes a single job within the processing pipeline.

    Args:
        session_path: The path to the session's data directory.
        base_job_name: The base job name (from BehaviorJobNames).
        session_name: The unique identifier of the session being processed.
        job_id: The unique hexadecimal identifier for this processing job.
        workers: The number of worker processes to use for parallel processing.
        tracker: The ProcessingTracker instance used to track the pipeline's runtime status.

    Returns:
        A tuple containing the job name, success status, and error message if failed.
    """
    full_job_name = f"{session_name}_{base_job_name}"

    try:
        _execute_job(
            session_path=session_path,
            job_name=full_job_name,
            job_id=job_id,
            workers=workers,
            tracker=tracker,
        )
    except Exception as error:
        return base_job_name, False, str(error)
    else:
        return base_job_name, True, None


def _run_processing_in_background(
    session_path: Path,
    base_jobs_to_run: list[str],
    workers: int,
) -> None:
    """Executes the processing pipeline in a background thread with sequential job execution.

    Runs jobs one at a time, with each job receiving all allocated CPU cores. Progress is tracked in the
    ProcessingTracker YAML file and can be queried via get_processing_status_tool.

    Args:
        session_path: The path to the session's data directory.
        base_jobs_to_run: The list of base job names to execute.
        workers: The number of CPU cores to use for each job.
    """
    session_key = str(session_path)

    try:
        # Loads the session data and initializes the processing tracker.
        session = SessionData.load(session_path=session_path)
        session_name = session.session_name
        tracker = ProcessingTracker(
            file_path=session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)
        )

        # Initializes the tracker file and gets job IDs.
        job_ids = _initialize_processing_tracker(
            session_path=session_path,
            session_name=session_name,
            base_job_names=base_jobs_to_run,
        )

        # Executes jobs sequentially, each with full worker allocation.
        for base_job_name in base_jobs_to_run:
            _execute_single_job(
                session_path=session_path,
                base_job_name=base_job_name,
                session_name=session_name,
                job_id=job_ids[f"{session_name}_{base_job_name}"],
                workers=workers,
                tracker=tracker,
            )
    except Exception:  # noqa: S110 - Exceptions are logged to the tracker by _execute_single_job.
        pass
    finally:
        # Cleans up session tracking state.
        _active_sessions.pop(session_key, None)


@mcp.tool()
def list_available_jobs_tool(session_path: str) -> str:
    """Discovers which processing jobs can run for a session based on existing .npz log files.

    Checks the session's behavior data directory to determine which log files exist and therefore which processing jobs
    are available to run.

    Args:
        session_path: The absolute path to the session's root data directory.

    Returns:
        A formatted list showing which jobs are available and which are not available.
    """
    try:
        path = Path(session_path)
        if not path.exists():
            return f"Error: Session path does not exist: {session_path}"

        available_jobs = _resolve_available_jobs(session_path=path)

        available = [name for name, exists in available_jobs.items() if exists]
        not_available = [name for name, exists in available_jobs.items() if not exists]

        result_lines = [f"Session: {session_path}"]
        if available:
            result_lines.append(f"Available jobs ({len(available)}): {', '.join(available)}")
        if not_available:
            result_lines.append(f"Not available ({len(not_available)}): {', '.join(not_available)}")

    except Exception as e:
        return f"Error: {e}"
    else:
        return "\n".join(result_lines)


def _get_session_status(session_path: Path) -> dict[str, str | int | list[tuple[str, str]]]:
    """Retrieves the processing status for a single session.

    Args:
        session_path: The path to the session's data directory.

    Returns:
        A dictionary containing session_name, status, progress (completed/total), current_job, and job_details.
    """
    session_key = str(session_path)

    # Checks if processing is actively running in a background thread.
    is_active = False
    if session_key in _active_sessions:
        thread = _active_sessions[session_key]
        if thread.is_alive():
            is_active = True
        else:
            del _active_sessions[session_key]

    # Extracts session name from path for display.
    session_display_name = session_path.name

    # Loads the session data to find the tracker file.
    session = SessionData.load(session_path=session_path)
    tracker_path = session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)

    if not tracker_path.exists():
        return {
            "session_name": session_display_name,
            "status": "NOT_STARTED",
            "completed": 0,
            "total": 0,
            "current_job": "-",
            "job_details": [],
        }

    tracker = ProcessingTracker.from_yaml(file_path=tracker_path)

    if not tracker.jobs:
        return {
            "session_name": session_display_name,
            "status": "NOT_STARTED",
            "completed": 0,
            "total": 0,
            "current_job": "-",
            "job_details": [],
        }

    # Generates reverse mapping from job_id to base_job_name.
    session_name = session.session_name
    id_to_name: dict[str, str] = {}
    for base_job_name in BehaviorJobNames:
        full_job_name = f"{session_name}_{base_job_name}"
        job_id = ProcessingTracker.generate_job_id(session_path=session_path, job_name=full_job_name)
        id_to_name[job_id] = base_job_name

    # Counts job statuses.
    succeeded_count = 0
    failed_count = 0
    pending_count = 0
    running_count = 0
    total_count = len(tracker.jobs)
    current_job = "-"
    job_details: list[tuple[str, str]] = []

    for job_id, job_state in tracker.jobs.items():
        job_name = id_to_name.get(job_id, job_id[:8])

        if job_state.status == ProcessingStatus.SUCCEEDED:
            succeeded_count += 1
            job_details.append((job_name, "done"))
        elif job_state.status == ProcessingStatus.FAILED:
            failed_count += 1
            job_details.append((job_name, "failed"))
        elif job_state.status == ProcessingStatus.RUNNING:
            running_count += 1
            current_job = job_name
            job_details.append((job_name, "running"))
        else:
            pending_count += 1
            job_details.append((job_name, "pending"))

    # Determines overall status.
    if is_active or running_count > 0:
        status = "PROCESSING"
    elif failed_count > 0 and succeeded_count > 0:
        status = "PARTIAL"
    elif failed_count > 0:
        status = "FAILED"
    elif succeeded_count == total_count:
        status = "SUCCEEDED"
    elif pending_count > 0:
        status = "PENDING"
    else:
        status = "UNKNOWN"

    return {
        "session_name": session_display_name,
        "status": status,
        "completed": succeeded_count,
        "total": total_count,
        "current_job": current_job,
        "job_details": job_details,
    }


def _format_status_table(statuses: list[dict[str, str | int | list[tuple[str, str]]]]) -> str:
    """Formats multiple session statuses as an ASCII table.

    Args:
        statuses: A list of status dictionaries from _get_session_status.

    Returns:
        A formatted ASCII table string.
    """
    from datetime import datetime

    # Calculates column widths.
    session_width = max(20, max(len(str(s["session_name"])) for s in statuses) + 2)
    status_width = 12
    progress_width = 10
    details_width = 25

    # Builds header.
    header_line = f"| {'Session':<{session_width}} | {'Status':<{status_width}} | {'Progress':<{progress_width}} | {'Details':<{details_width}} |"
    separator = f"+{'-' * (session_width + 2)}+{'-' * (status_width + 2)}+{'-' * (progress_width + 2)}+{'-' * (details_width + 2)}+"
    title_width = len(separator) - 2
    title = "Behavior Processing Status"
    title_line = f"|{title:^{title_width}}|"

    lines = [separator, title_line, separator, header_line, separator]

    # Builds data rows.
    for status in statuses:
        session_name = str(status["session_name"])
        status_str = str(status["status"])
        completed = status["completed"]
        total = status["total"]
        progress = f"{completed}/{total} jobs"
        current = str(status["current_job"])

        # Generates details string.
        if status_str == "PROCESSING":
            details = f"Running: {current}"
        elif status_str == "SUCCEEDED":
            details = "Complete"
        elif status_str == "FAILED":
            details = "Failed - check logs"
        elif status_str == "PARTIAL":
            details = "Some jobs failed"
        elif status_str == "PENDING":
            details = "Queued"
        else:
            details = "-"

        # Truncates if needed.
        if len(session_name) > session_width:
            session_name = session_name[: session_width - 3] + "..."
        if len(details) > details_width:
            details = details[: details_width - 3] + "..."

        row = f"| {session_name:<{session_width}} | {status_str:<{status_width}} | {progress:<{progress_width}} | {details:<{details_width}} |"
        lines.append(row)

    lines.append(separator)
    lines.append(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


@mcp.tool()
def get_processing_status_tool(session_path: str) -> str:
    """Checks the processing status for a session with per-job progress details.

    Determines whether processing is actively running in the background, has completed successfully, has failed, or has
    not been started. Returns detailed per-job progress by reading from the ProcessingTracker YAML file.

    Args:
        session_path: The absolute path to the session's root data directory.

    Returns:
        The current processing status with per-job details.
    """
    try:
        path = Path(session_path)
        if not path.exists():
            return f"Error: Session path does not exist: {session_path}"

        status = _get_session_status(session_path=path)
        table = _format_status_table(statuses=[status])

    except Exception as e:
        return f"Error: {e}"
    else:
        return table


@mcp.tool()
def get_batch_processing_status_tool(session_paths: list[str]) -> str:
    """Checks the processing status for multiple sessions and returns a combined formatted table.

    Polls all specified sessions and displays their status in a single table. This is more efficient than calling
    get_processing_status_tool multiple times when monitoring a batch of sessions.

    Important:
        AI agents SHOULD poll status no more frequently than once every 2 minutes to avoid excessive API calls.
        Processing typically takes several minutes per session depending on data size.

    Args:
        session_paths: A list of absolute paths to session root data directories.

    Returns:
        A formatted ASCII table showing the status of all sessions.
    """
    if not session_paths:
        return "Error: No session paths provided"

    statuses: list[dict[str, str | int | list[tuple[str, str]]]] = []
    errors: list[str] = []

    for session_path in session_paths:
        try:
            path = Path(session_path)
            if not path.exists():
                errors.append(f"Path not found: {session_path}")
                continue
            status = _get_session_status(session_path=path)
            statuses.append(status)
        except Exception as e:
            errors.append(f"Error for {session_path}: {e}")

    if not statuses:
        return "Error: No valid sessions found.\n" + "\n".join(errors)

    table = _format_status_table(statuses=statuses)

    if errors:
        table += "\n\nWarnings:\n" + "\n".join(f"  - {err}" for err in errors)

    return table


@mcp.tool()
def start_processing_tool(
    session_path: str,
    *,
    process_runtime: bool = True,
    process_face_camera: bool = True,
    process_body_camera: bool = True,
    process_actor_microcontroller: bool = True,
    process_sensor_microcontroller: bool = True,
    process_encoder_microcontroller: bool = True,
    workers: int = -1,
) -> str:
    """Starts behavior data processing in the background with sequential job execution.

    Launches processing in a background thread with jobs running sequentially. Each job receives all allocated CPU
    cores, maximizing throughput per job. This approach allows multiple sessions to be processed in parallel by
    starting separate background threads for each session.

    Important:
        The AI agent calling this tool should use get_processing_status_tool to monitor progress after starting
        processing. The status tool will show per-job progress.

    Args:
        session_path: The absolute path to the session's root data directory.
        process_runtime: Determines whether to process the session runtime data.
        process_face_camera: Determines whether to process the face camera timestamps.
        process_body_camera: Determines whether to process the body camera timestamps.
        process_actor_microcontroller: Determines whether to process the Actor microcontroller data.
        process_sensor_microcontroller: Determines whether to process the Sensor microcontroller data.
        process_encoder_microcontroller: Determines whether to process the Encoder microcontroller data.
        workers: The number of CPU cores to use per job. Set to -1 to use the default (available cores minus 4,
            capped at 30).

    Returns:
        A confirmation message showing the number of jobs started and the worker count.
    """
    try:
        path = Path(session_path)
        if not path.exists():
            return f"Error: Session path does not exist: {session_path}"

        session_key = str(path)

        # Checks if processing is already running for this session.
        if session_key in _active_sessions:
            thread = _active_sessions[session_key]
            if thread.is_alive():
                return f"Error: Processing already in progress for session: {session_path}"
            # Previous thread finished, clean up.
            del _active_sessions[session_key]

        # Verifies the session can be loaded before starting the background thread.
        SessionData.load(session_path=path)

        # Resolves which jobs are available based on existing log files.
        available_jobs = _resolve_available_jobs(session_path=path)

        # Maps base job names to their requested flags.
        requested_jobs: dict[str, bool] = {
            BehaviorJobNames.RUNTIME: process_runtime,
            BehaviorJobNames.FACE_CAMERA: process_face_camera,
            BehaviorJobNames.BODY_CAMERA: process_body_camera,
            BehaviorJobNames.ACTOR_MICROCONTROLLER: process_actor_microcontroller,
            BehaviorJobNames.SENSOR_MICROCONTROLLER: process_sensor_microcontroller,
            BehaviorJobNames.ENCODER_MICROCONTROLLER: process_encoder_microcontroller,
        }

        # If all requested job flags are False, treats them as all True (process all available jobs).
        if not any(requested_jobs.values()):
            requested_jobs = dict.fromkeys(requested_jobs, True)

        # Determines which base jobs to run (requested AND available).
        base_jobs_to_run = [
            base_job_name
            for base_job_name, requested in requested_jobs.items()
            if requested and available_jobs[base_job_name]
        ]

        if not base_jobs_to_run:
            return f"Error: No jobs available to run for session: {session_path}"

        # Calculates workers for sequential job execution.
        job_workers = _calculate_job_workers(requested_workers=workers)

        # Creates and starts the background processing thread.
        thread = Thread(
            target=_run_processing_in_background,
            kwargs={
                "session_path": path,
                "base_jobs_to_run": base_jobs_to_run,
                "workers": job_workers,
            },
            daemon=True,
        )
        thread.start()

        # Stores the thread reference for status tracking.
        _active_sessions[session_key] = thread

    except Exception as e:
        return f"Error: {e}"
    else:
        return f"Processing started: {len(base_jobs_to_run)} jobs | Workers: {job_workers} | Session: {session_path}"


@mcp.tool()
def check_output_files_tool(session_path: str) -> str:
    """Verifies which .feather output files exist in the session's processed data directory.

    Lists all .feather files that have been generated by the processing pipeline, along with their file sizes.

    Args:
        session_path: The absolute path to the session's root data directory.

    Returns:
        A formatted list of output files with sizes, or a message indicating no files exist.
    """
    try:
        path = Path(session_path)
        if not path.exists():
            return f"Error: Session path does not exist: {session_path}"

        session = SessionData.load(session_path=path)
        output_directory = session.processed_data.behavior_data_path

        if not output_directory.exists():
            return f"No output directory found: {output_directory}"

        feather_files = sorted(output_directory.glob("*.feather"))

        if not feather_files:
            return f"No .feather files found in: {output_directory}"

        result_lines = [f"Output directory: {output_directory}", f"Files ({len(feather_files)}):"]
        for file_path in feather_files:
            size_bytes = file_path.stat().st_size
            if size_bytes >= _BYTES_PER_KB * _BYTES_PER_KB:
                size_str = f"{size_bytes / (_BYTES_PER_KB * _BYTES_PER_KB):.1f} MB"
            elif size_bytes >= _BYTES_PER_KB:
                size_str = f"{size_bytes / _BYTES_PER_KB:.1f} KB"
            else:
                size_str = f"{size_bytes} B"
            result_lines.append(f"  {file_path.name} ({size_str})")

    except Exception as e:
        return f"Error: {e}"
    else:
        return "\n".join(result_lines)


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)


def run_mcp_server() -> None:
    """Starts the MCP server with stdio transport.

    Intended to be used as a CLI entry point.
    """
    run_server(transport="stdio")
