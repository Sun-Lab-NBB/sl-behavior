from pathlib import Path

from .legacy import extract_gimbl_data as extract_gimbl_data
from .log_processing import extract_log_data as extract_log_data

def extract_behavior_data(
    session_path: Path,
    processed_data_root: Path,
    legacy: bool,
    create_processed_directories: bool,
    update_manifest: bool,
) -> None: ...
