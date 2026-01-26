"""Provides the MCP server for agentic behavior data processing.

Exposes tools that enable AI agents to discover available processing jobs, start processing in the background, monitor
processing status, and verify output files.
"""

from typing import Literal
from pathlib import Path
from threading import Thread

from sl_shared_assets import SessionData, ProcessingStatus, ProcessingTracker, ProcessingTrackers
from mcp.server.fastmcp import FastMCP

from .pipeline import BehaviorJobNames, process_session, _resolve_available_jobs

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sl-behavior", json_response=True)

# Module-level state for tracking active processing sessions.
_active_sessions: dict[str, Thread] = {}

# Bytes per kilobyte, used for file size formatting.
_BYTES_PER_KB: int = 1024


def _run_processing_in_background(
    session_path: Path,
    *,
    process_runtime: bool,
    process_face_camera: bool,
    process_body_camera: bool,
    process_actor_microcontroller: bool,
    process_sensor_microcontroller: bool,
    process_encoder_microcontroller: bool,
    workers: int,
) -> None:
    """Executes the processing pipeline in a background thread.

    Wraps the process_session call to handle exceptions gracefully within the thread context. Any exceptions are
    caught and logged to the processing tracker as job failures.

    Args:
        session_path: The path to the session's data directory.
        process_runtime: Determines whether to process the session runtime data.
        process_face_camera: Determines whether to process the face camera timestamps.
        process_body_camera: Determines whether to process the body camera timestamps.
        process_actor_microcontroller: Determines whether to process the Actor microcontroller data.
        process_sensor_microcontroller: Determines whether to process the Sensor microcontroller data.
        process_encoder_microcontroller: Determines whether to process the Encoder microcontroller data.
        workers: The number of worker processes to use for parallel processing.
    """
    try:
        process_session(
            session_path=session_path,
            process_runtime=process_runtime,
            process_face_camera=process_face_camera,
            process_body_camera=process_body_camera,
            process_actor_microcontroller=process_actor_microcontroller,
            process_sensor_microcontroller=process_sensor_microcontroller,
            process_encoder_microcontroller=process_encoder_microcontroller,
            workers=workers,
        )
    except Exception:  # noqa: S110 - Exceptions are logged to the tracker by process_session.
        pass
    finally:
        # Removes the session from active sessions when processing completes or fails.
        session_key = str(session_path)
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


@mcp.tool()
def get_processing_status_tool(session_path: str) -> str:
    """Checks the processing status for a session.

    Determines whether processing is actively running in the background, has completed successfully, has failed, or has
    not been started.

    Args:
        session_path: The absolute path to the session's root data directory.

    Returns:
        The current processing status: PROCESSING, SUCCEEDED, FAILED, PARTIAL, or NOT_STARTED.
    """
    try:
        path = Path(session_path)
        if not path.exists():
            return f"Error: Session path does not exist: {session_path}"

        session_key = str(path)

        # Checks if processing is actively running in a background thread.
        if session_key in _active_sessions:
            thread = _active_sessions[session_key]
            if thread.is_alive():
                return f"Status: PROCESSING | Session: {session_path}"
            # Thread finished, clean up the reference.
            del _active_sessions[session_key]

        # Loads the session data to find the tracker file.
        session = SessionData.load(session_path=path)
        tracker_path = session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)

        if not tracker_path.exists():
            return f"Status: NOT_STARTED | Session: {session_path}"

        # Loads the tracker and analyzes job statuses.
        tracker = ProcessingTracker.from_yaml(file_path=tracker_path)

        if not tracker.jobs:
            return f"Status: NOT_STARTED | Session: {session_path}"

        succeeded_count = sum(1 for job in tracker.jobs.values() if job.status == ProcessingStatus.SUCCEEDED)
        failed_count = sum(1 for job in tracker.jobs.values() if job.status == ProcessingStatus.FAILED)
        pending_count = sum(1 for job in tracker.jobs.values() if job.status == ProcessingStatus.SCHEDULED)
        running_count = sum(1 for job in tracker.jobs.values() if job.status == ProcessingStatus.RUNNING)
        total_count = len(tracker.jobs)

        if running_count > 0:
            status_message = f"Status: PROCESSING | Running: {running_count}/{total_count} | Session: {session_path}"
        elif failed_count > 0 and succeeded_count > 0:
            status_message = (
                f"Status: PARTIAL | Succeeded: {succeeded_count}, Failed: {failed_count} | Session: {session_path}"
            )
        elif failed_count > 0:
            status_message = f"Status: FAILED | Failed: {failed_count}/{total_count} | Session: {session_path}"
        elif succeeded_count == total_count:
            status_message = f"Status: SUCCEEDED | Completed: {succeeded_count}/{total_count} | Session: {session_path}"
        elif pending_count > 0:
            status_message = f"Status: PENDING | Pending: {pending_count}/{total_count} | Session: {session_path}"
        else:
            status_message = f"Status: UNKNOWN | Session: {session_path}"

    except Exception as e:
        return f"Error: {e}"
    else:
        return status_message


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
    """Starts behavior data processing in the background and returns immediately.

    Launches processing in a background thread, allowing the AI agent to monitor progress via get_processing_status_tool
    or start processing multiple sessions in parallel.

    Important:
        The AI agent calling this tool should use get_processing_status_tool to monitor progress after starting
        processing. Multiple sessions can be started in parallel and monitored independently.

    Args:
        session_path: The absolute path to the session's root data directory.
        process_runtime: Determines whether to process the session runtime data.
        process_face_camera: Determines whether to process the face camera timestamps.
        process_body_camera: Determines whether to process the body camera timestamps.
        process_actor_microcontroller: Determines whether to process the Actor microcontroller data.
        process_sensor_microcontroller: Determines whether to process the Sensor microcontroller data.
        process_encoder_microcontroller: Determines whether to process the Encoder microcontroller data.
        workers: The number of worker processes to use. Set to -1 to use all available CPU cores.

    Returns:
        A confirmation message indicating processing has started, or an error message.
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

        # Creates and starts the background processing thread.
        thread = Thread(
            target=_run_processing_in_background,
            kwargs={
                "session_path": path,
                "process_runtime": process_runtime,
                "process_face_camera": process_face_camera,
                "process_body_camera": process_body_camera,
                "process_actor_microcontroller": process_actor_microcontroller,
                "process_sensor_microcontroller": process_sensor_microcontroller,
                "process_encoder_microcontroller": process_encoder_microcontroller,
                "workers": workers,
            },
            daemon=True,
        )
        thread.start()

        # Stores the thread reference for status tracking.
        _active_sessions[session_key] = thread

        # Builds a summary of requested jobs.
        requested_jobs = []
        if process_runtime:
            requested_jobs.append(BehaviorJobNames.RUNTIME)
        if process_face_camera:
            requested_jobs.append(BehaviorJobNames.FACE_CAMERA)
        if process_body_camera:
            requested_jobs.append(BehaviorJobNames.BODY_CAMERA)
        if process_actor_microcontroller:
            requested_jobs.append(BehaviorJobNames.ACTOR_MICROCONTROLLER)
        if process_sensor_microcontroller:
            requested_jobs.append(BehaviorJobNames.SENSOR_MICROCONTROLLER)
        if process_encoder_microcontroller:
            requested_jobs.append(BehaviorJobNames.ENCODER_MICROCONTROLLER)

        jobs_summary = "all available jobs" if not requested_jobs else f"{len(requested_jobs)} jobs"

    except Exception as e:
        return f"Error: {e}"
    else:
        return f"Processing started: {jobs_summary} | Workers: {workers} | Session: {session_path}"


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
