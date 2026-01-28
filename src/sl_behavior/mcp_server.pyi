from typing import Any, Literal
from pathlib import Path
from threading import Lock, Thread
from dataclasses import field, dataclass

from _typeshed import Incomplete
from sl_shared_assets import SessionTypes, ProcessingTracker

from .pipeline import (
    BehaviorJobNames as BehaviorJobNames,
    _execute_job as _execute_job,
    get_session_root as get_session_root,
    _resolve_available_jobs as _resolve_available_jobs,
    _initialize_processing_tracker as _initialize_processing_tracker,
)

mcp: Incomplete
_RESERVED_CORES: int
_MAXIMUM_JOB_CORES: int
_PROCESSABLE_SESSION_TYPES: frozenset[SessionTypes]

@dataclass
class _BatchState:
    queued: list[Path] = field(default_factory=list)
    active: dict[str, Thread] = field(default_factory=dict)
    completed: set[str] = field(default_factory=set)
    failed: set[str] = field(default_factory=set)
    errors: dict[str, list[str]] = field(default_factory=dict)
    job_flags: dict[str, bool] = field(default_factory=dict)
    workers: int = ...
    max_parallel: int = ...
    lock: Lock = field(default_factory=Lock)
    manager_thread: Thread | None = ...

_batch_state: _BatchState | None

def _calculate_job_workers(requested_workers: int) -> int: ...
def _calculate_max_parallel_sessions() -> int: ...
def _execute_single_job(
    session_path: Path, base_job_name: str, session_name: str, job_id: str, workers: int, tracker: ProcessingTracker
) -> tuple[str, bool, str | None]: ...
def _run_session_processing(session_path: Path, job_flags: dict[str, bool], workers: int) -> tuple[bool, list[str]]: ...
def _session_worker(session_path: Path, job_flags: dict[str, bool], workers: int) -> None: ...
def _batch_manager() -> None: ...
def _get_session_status(session_path: Path) -> dict[str, Any]: ...
def discover_sessions_tool(root_directory: str) -> dict[str, Any]: ...
def get_processing_status_tool() -> dict[str, Any]: ...
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
) -> dict[str, Any]: ...
def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None: ...
