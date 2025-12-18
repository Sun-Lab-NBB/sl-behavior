from enum import StrEnum
from pathlib import Path

from .camera import (
    CameraLogIds as CameraLogIds,
    process_camera_timestamps as process_camera_timestamps,
)
from .runtime import process_runtime_data as process_runtime_data
from .microcontrollers import (
    MicrocontrollerLogIds as MicrocontrollerLogIds,
    process_microcontroller_data as process_microcontroller_data,
)

class BehaviorJobNames(StrEnum):
    RUNTIME = "runtime_processing"
    FACE_CAMERA = "face_camera_processing"
    BODY_CAMERA = "body_camera_processing"
    ACTOR_MICROCONTROLLER = "actor_microcontroller_processing"
    SENSOR_MICROCONTROLLER = "sensor_microcontroller_processing"
    ENCODER_MICROCONTROLLER = "encoder_microcontroller_processing"

def _resolve_available_jobs(session_path: Path) -> dict[str, bool]: ...
def _generate_job_ids(session_path: Path, job_names: list[str]) -> dict[str, str]: ...
def _initialize_processing_tracker(session_path: Path, job_names: list[str]) -> dict[str, str]: ...
def process_session(
    session_path: Path,
    job_id: str | None = None,
    *,
    process_runtime: bool = False,
    process_face_camera: bool = False,
    process_body_camera: bool = False,
    process_actor_microcontroller: bool = False,
    process_sensor_microcontroller: bool = False,
    process_encoder_microcontroller: bool = False,
    workers: int = -1,
) -> None: ...
def _run_single_job(session_path: Path, job_id: str, workers: int) -> None: ...
def _run_job_by_name(session_path: Path, job_name: str, job_id: str, workers: int) -> None: ...
