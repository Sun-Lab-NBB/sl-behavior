from pathlib import Path

from _typeshed import Incomplete

from .pipeline import process_session as process_session
from .mcp_server import run_server as run_server

CONTEXT_SETTINGS: Incomplete

def cli() -> None: ...
def process(
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
def mcp(transport: str) -> None: ...
