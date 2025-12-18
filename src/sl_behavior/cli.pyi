from pathlib import Path

from _typeshed import Incomplete

from .pipeline import process_session as process_session

CONTEXT_SETTINGS: Incomplete

def behavior(
    session_path: Path,
    job_id: str | None,
    *,
    runtime: bool,
    face_camera: bool,
    body_camera: bool,
    actor: bool,
    sensor: bool,
    encoder: bool,
    workers: int,
) -> None: ...
