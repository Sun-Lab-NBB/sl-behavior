from pathlib import Path

import click
import numpy as np
from sl_shared_assets import SessionData
from ataraxis_base_utilities import console

from .path_tools import verify_checksum
from .log_processing import process_log_directories

@click.command()
@click.option(
    "-p",
    "--path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    prompt="Enter the path of the project session to verify",
    help="The path to the session directory to be processed.",
)
@click.option(
    "-s",
    "--on_server",
    is_flag=True,
    required=True,
    default=False,
    help="Determines whether the CLI is called on the Sun lab BioHPC server or a local machine.",
)
def check_session(path: str, on_server: bool):
    session_path = Path(path)
    session_data = SessionData.load(session_path=session_path, on_server=on_server)

    extract_npz(session_data=session_data)
    run_checksum(session_data=session_data)


def extract_npz(session_data: SessionData) -> None:
    """
    Processes NPZ files from the raw_data/behavior_data subdirectory and saves processed feather files in the
    processed_data/behavior_data subdirectory.

    Args:
        session_data: The SessionData class instance initialized from the session_data.yaml file stored inside the
                      processed session's raw_data folder.
    """
    raw_data_path = session_data.raw_data.raw_data_path
    process_log_directories(data_directory=raw_data_path, verbose=True)


def run_checksum(session_data: SessionData):
    """
    Calls the verify_checksum function to check if the calculated checksum matches the stored checksum. If they match,
    the telomere.bin file is created in the raw_data directory.

    Args:
        session_data: The SessionData class instance initialized from the session_data.yaml file stored inside the
                      processed session's raw_data folder.
    """
    checksum_true = verify_checksum(session_data=session_data)

    if checksum_true:
        raw_data_dir = session_data.raw_data.raw_data_path
        telomere_file_path = raw_data_dir / "telomere.bin"
        telomere_file_path.touch()
