"""Provides the MCP server for agentic behavior data processing.

Exposes tools that enable AI agents to discover available processing jobs, start processing in the background, and
monitor processing status.
"""

from __future__ import annotations

from os import cpu_count
from typing import Any, Literal
from pathlib import Path
from threading import Lock, Thread
from dataclasses import field, dataclass

from sl_shared_assets import SessionData, ProcessingStatus, ProcessingTracker, ProcessingTrackers
from mcp.server.fastmcp import FastMCP

from .pipeline import (
    BehaviorJobNames,
    _execute_job,
    get_session_root,
    _resolve_available_jobs,
    _initialize_processing_tracker,
)

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sl-behavior", json_response=True)

# CPU cores reserved for system operations.
_RESERVED_CORES: int = 4

# Maximum CPU cores any single job can use.
_MAXIMUM_JOB_CORES: int = 30


@dataclass
class _BatchState:
    """Tracks state for batch processing operations."""

    queued: list[Path] = field(default_factory=list)
    active: dict[str, Thread] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    job_flags: dict[str, bool] = field(default_factory=dict)
    workers: int = -1
    max_parallel: int = 1
    lock: Lock = field(default_factory=Lock)
    manager_thread: Thread | None = None


# Module-level batch processing state.
_batch_state: _BatchState | None = None


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


def _calculate_max_parallel_sessions() -> int:
    """Calculates the maximum number of sessions that can run in parallel.

    Uses the formula: floor((cpu_count + 15) / 30) to determine optimal parallelization.

    Returns:
        The maximum number of parallel sessions.
    """
    available_cores = cpu_count()
    if available_cores is None:
        return 1

    return max(1, (available_cores + 15) // _MAXIMUM_JOB_CORES)


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


def _run_session_processing(
    session_path: Path,
    job_flags: dict[str, bool],
    workers: int,
) -> bool:
    """Executes the processing pipeline for a single session.

    Runs jobs sequentially, with each job receiving all allocated CPU cores.

    Args:
        session_path: The path to the session's data directory.
        job_flags: Dictionary mapping job names to whether they should run.
        workers: The number of CPU cores to use for each job.

    Returns:
        True if all jobs succeeded, False if any failed.
    """
    try:
        # Loads the session data and initializes the processing tracker.
        session = SessionData.load(session_path=session_path)
        session_name = session.session_name
        tracker = ProcessingTracker(
            file_path=session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)
        )

        # Resolves which jobs are available based on existing log files.
        available_jobs = _resolve_available_jobs(session_path=session_path)

        # Determines which base jobs to run (requested AND available).
        base_jobs_to_run = [
            base_job_name
            for base_job_name, requested in job_flags.items()
            if requested and available_jobs[base_job_name]
        ]

        if not base_jobs_to_run:
            return True  # No jobs to run is considered success.

        # Initializes the tracker file and gets job IDs.
        job_ids = _initialize_processing_tracker(session_path=session_path, base_job_names=base_jobs_to_run)

        # Executes jobs sequentially, each with full worker allocation.
        all_succeeded = True
        for base_job_name in base_jobs_to_run:
            _, succeeded, _ = _execute_single_job(
                session_path=session_path,
                base_job_name=base_job_name,
                session_name=session_name,
                job_id=job_ids[f"{session_name}_{base_job_name}"],
                workers=workers,
                tracker=tracker,
            )
            if not succeeded:
                all_succeeded = False

    except Exception:
        return False
    else:
        return all_succeeded


def _session_worker(session_path: Path, job_flags: dict[str, bool], workers: int) -> None:
    """Worker function that processes a session and updates batch state on completion.

    Args:
        session_path: The path to the session's data directory.
        job_flags: Dictionary mapping job names to whether they should run.
        workers: The number of CPU cores to use for each job.
    """
    global _batch_state

    session_key = str(session_path)
    success = _run_session_processing(session_path=session_path, job_flags=job_flags, workers=workers)

    if _batch_state is not None:
        with _batch_state.lock:
            # Removes from active, adds to completed or failed.
            _batch_state.active.pop(session_key, None)
            if success:
                _batch_state.completed.add(session_key)
            else:
                _batch_state.failed.add(session_key)


def _batch_manager() -> None:
    """Manager thread that monitors active sessions and starts queued sessions.

    Runs continuously until all sessions are processed (queue empty and no active sessions).
    """
    global _batch_state

    if _batch_state is None:
        return

    while True:
        with _batch_state.lock:
            # Cleans up finished threads from active.
            finished_keys = [key for key, thread in _batch_state.active.items() if not thread.is_alive()]
            for key in finished_keys:
                _batch_state.active.pop(key, None)

            # Checks if we're done (no active, no queued).
            if not _batch_state.active and not _batch_state.queued:
                break

            # Starts new sessions if we have capacity.
            while len(_batch_state.active) < _batch_state.max_parallel and _batch_state.queued:
                next_session = _batch_state.queued.pop(0)
                session_key = str(next_session)

                thread = Thread(
                    target=_session_worker,
                    kwargs={
                        "session_path": next_session,
                        "job_flags": _batch_state.job_flags,
                        "workers": _batch_state.workers,
                    },
                    daemon=True,
                )
                thread.start()
                _batch_state.active[session_key] = thread

        # Sleeps briefly before checking again.
        import time

        time.sleep(1.0)


def _get_session_status(session_path: Path) -> dict[str, Any]:
    """Retrieves the processing status for a single session.

    Args:
        session_path: The path to the session's data directory.

    Returns:
        A dictionary containing session_name, status, progress (completed/total), current_job, and job_details.
    """
    global _batch_state

    session_key = str(session_path)

    # Checks batch state for queue/active/completed status.
    is_queued = False
    is_active = False
    is_completed = False
    is_failed = False

    if _batch_state is not None:
        with _batch_state.lock:
            is_queued = session_path in _batch_state.queued
            is_active = session_key in _batch_state.active and _batch_state.active[session_key].is_alive()
            is_completed = session_key in _batch_state.completed
            is_failed = session_key in _batch_state.failed

    # Extracts session name from path for display.
    session_display_name = session_path.name

    # If queued, returns early with QUEUED status.
    if is_queued:
        return {
            "session_name": session_display_name,
            "status": "QUEUED",
            "completed": 0,
            "total": 0,
            "current_job": "-",
            "job_details": [],
        }

    # Loads the session data to find the tracker file.
    try:
        session = SessionData.load(session_path=session_path)
    except Exception:
        return {
            "session_name": session_display_name,
            "status": "ERROR",
            "completed": 0,
            "total": 0,
            "current_job": "-",
            "job_details": [],
        }

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

    # Generates reverse mapping from job_id to base_job_name using the canonical session root path.
    session_root = get_session_root(session)
    session_name = session.session_name
    id_to_name: dict[str, str] = {}
    for base_job_name in BehaviorJobNames:
        full_job_name = f"{session_name}_{base_job_name}"
        job_id = ProcessingTracker.generate_job_id(session_path=session_root, job_name=full_job_name)
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
    elif is_failed or (failed_count > 0 and succeeded_count == 0):
        status = "FAILED"
    elif failed_count > 0 and succeeded_count > 0:
        status = "PARTIAL"
    elif is_completed or succeeded_count == total_count:
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


@mcp.tool()
def get_processing_status_tool() -> dict[str, Any]:
    """Returns the current processing status for all sessions being managed.

    Returns status for active, queued, and completed sessions. If no batch processing is active, returns an empty
    status indicating no sessions are being processed.

    Returns:
        A dictionary containing:
        - sessions: List of status dictionaries for each session (active, queued, completed)
        - summary: Overall progress statistics (total, completed, failed, processing, queued)
    """
    global _batch_state

    if _batch_state is None:
        return {
            "sessions": [],
            "summary": {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "processing": 0,
                "queued": 0,
            },
        }

    session_statuses: list[dict[str, Any]] = []

    with _batch_state.lock:
        # Collects all session paths.
        all_sessions: list[Path] = []

        # Adds active sessions.
        for session_key in _batch_state.active:
            all_sessions.append(Path(session_key))

        # Adds queued sessions.
        all_sessions.extend(_batch_state.queued)

        # Adds completed sessions.
        for session_key in _batch_state.completed:
            all_sessions.append(Path(session_key))

        # Adds failed sessions.
        for session_key in _batch_state.failed:
            if Path(session_key) not in all_sessions:
                all_sessions.append(Path(session_key))

        queued_count = len(_batch_state.queued)
        processing_count = len(_batch_state.active)
        succeeded_count = len(_batch_state.completed)
        failed_count = len(_batch_state.failed)

    # Gets status for each session (outside lock to avoid blocking).
    for session_path in all_sessions:
        status = _get_session_status(session_path=session_path)
        session_statuses.append(status)

    # Sorts sessions: processing first, then queued, then completed/failed.
    status_order = {"PROCESSING": 0, "QUEUED": 1, "PENDING": 2, "SUCCEEDED": 3, "PARTIAL": 4, "FAILED": 5}
    session_statuses.sort(key=lambda s: (status_order.get(s["status"], 99), s["session_name"]))

    return {
        "sessions": session_statuses,
        "summary": {
            "total": len(all_sessions),
            "succeeded": succeeded_count,
            "failed": failed_count,
            "processing": processing_count,
            "queued": queued_count,
        },
    }


@mcp.tool()
def start_processing_tool(
    session_paths: list[str],
    *,
    process_runtime: bool = True,
    process_face_camera: bool = True,
    process_body_camera: bool = True,
    process_actor_microcontroller: bool = True,
    process_sensor_microcontroller: bool = True,
    process_encoder_microcontroller: bool = True,
    workers: int = -1,
) -> dict[str, Any]:
    """Starts behavior data processing for one or more sessions.

    Accepts a list of session paths and manages them as a batch. Sessions are processed in parallel up to the
    calculated maximum based on available CPU cores. Remaining sessions are queued and automatically started as
    earlier sessions complete.

    The tool returns immediately after starting the batch. Use get_processing_status_tool to monitor progress.

    Args:
        session_paths: List of absolute paths to session root data directories. Minimum of 1 session required.
        process_runtime: Whether to process the session runtime data.
        process_face_camera: Whether to process the face camera timestamps.
        process_body_camera: Whether to process the body camera timestamps.
        process_actor_microcontroller: Whether to process the Actor microcontroller data.
        process_sensor_microcontroller: Whether to process the Sensor microcontroller data.
        process_encoder_microcontroller: Whether to process the Encoder microcontroller data.
        workers: The number of CPU cores to use per job. Set to -1 for automatic allocation.

    Returns:
        A dictionary containing confirmation of started sessions, queued sessions, and worker allocation.
    """
    global _batch_state

    if not session_paths:
        return {"error": "At least one session path is required"}

    # Validates all session paths exist.
    valid_paths: list[Path] = []
    invalid_paths: list[str] = []

    for session_path in session_paths:
        path = Path(session_path)
        if path.exists():
            valid_paths.append(path)
        else:
            invalid_paths.append(session_path)

    if not valid_paths:
        return {"error": "No valid session paths provided", "invalid_paths": invalid_paths}

    # Checks if processing is already active.
    if _batch_state is not None:
        with _batch_state.lock:
            if _batch_state.active or _batch_state.queued:
                return {
                    "error": "Processing already in progress. Wait for current batch to complete or check status.",
                    "active_count": len(_batch_state.active),
                    "queued_count": len(_batch_state.queued),
                }

    # Builds job flags dictionary.
    job_flags: dict[str, bool] = {
        BehaviorJobNames.RUNTIME: process_runtime,
        BehaviorJobNames.FACE_CAMERA: process_face_camera,
        BehaviorJobNames.BODY_CAMERA: process_body_camera,
        BehaviorJobNames.ACTOR_MICROCONTROLLER: process_actor_microcontroller,
        BehaviorJobNames.SENSOR_MICROCONTROLLER: process_sensor_microcontroller,
        BehaviorJobNames.ENCODER_MICROCONTROLLER: process_encoder_microcontroller,
    }

    # If all flags are False, treats as all True.
    if not any(job_flags.values()):
        job_flags = dict.fromkeys(job_flags, True)

    # Calculates resource allocation.
    job_workers = _calculate_job_workers(requested_workers=workers)
    max_parallel = _calculate_max_parallel_sessions()

    # Initializes batch state.
    _batch_state = _BatchState(
        queued=list(valid_paths),
        active={},
        completed=set(),
        failed=set(),
        job_flags=job_flags,
        workers=job_workers,
        max_parallel=max_parallel,
        lock=Lock(),
        manager_thread=None,
    )

    # Starts the batch manager thread.
    manager = Thread(target=_batch_manager, daemon=True)
    manager.start()
    _batch_state.manager_thread = manager

    # Calculates how many will start immediately vs queue.
    immediate_start = min(len(valid_paths), max_parallel)
    queued_count = len(valid_paths) - immediate_start

    result: dict[str, Any] = {
        "started": True,
        "total_sessions": len(valid_paths),
        "immediate_start": immediate_start,
        "queued": queued_count,
        "max_parallel": max_parallel,
        "workers_per_session": job_workers,
    }

    if invalid_paths:
        result["invalid_paths"] = invalid_paths

    return result


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
