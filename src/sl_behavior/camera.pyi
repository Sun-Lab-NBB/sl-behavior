from enum import IntEnum
from pathlib import Path

class CameraLogIds(IntEnum):
    FACE = 51
    BODY = 62

CAMERA_OUTPUT_NAMES: dict[int, str]

def process_camera_timestamps(session_path: Path, log_id: int, workers: int = -1) -> None: ...
