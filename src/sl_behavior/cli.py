"""This module provides the Command-Line Interfaces (CLIs) for processing behavior data acquired in the Sun lab. Most
of these CLIs are intended to run on the remote compute server and should not be used by end-users directly."""

from pathlib import Path

import click
from sl_shared_assets import SessionData

from .camera import process_camera_timestamps
from .runtime import process_runtime_data
from .microcontrollers import process_microcontroller_data

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS = dict(max_content_width=120)  # or any width you want


@click.group("behavior", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-sp",
    "--session-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help=(
        "The absolute path to the root session directory to process. This directory must contain the 'raw_data' "
        "subdirectory."
    ),
)
@click.option(
    "-pdr",
    "--processed-data-root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory that stores the processed data from all Sun lab projects, if it is "
        "different from the root directory included in the 'session-path' argument value."
    ),
)
@click.option(
    "-id",
    "--manager-id",
    type=int,
    required=True,
    default=0,
    show_default=True,
    help="The unique identifier of the process that manages this runtime.",
)
@click.option(
    "-r",
    "--reset-tracker",
    is_flag=True,
    required=False,
    help=(
        "Determines whether to forcibly reset the tracker file for the target session management pipeline before "
        "processing runtime. This flag should only be used in exceptional cases to recover from improper runtime "
        "terminations."
    ),
)
def behavior() -> None:
    """This Command-Line Interface (CLI) allows processing behavior data acquired the Sun lab.

    This CLI is intended to run on the Sun lab remote compute server(s) and should not be called by the end-user
    directly. Instead, commands from this CLI are designed to be accessed through the bindings in the sl-forgery
    library.
    """


@click.command()
@click.option(
    "-l",
    "--log_id",
    type=int,
    required=True,
    show_default=True,
    help=(
        "The xxHash-64 hash value that represents the unique identifier for the process that manages this runtime. "
        "This is primarily used when calling this CLI on remote compute servers to ensure that only a single process "
        "can execute the CLI at a time."
    ),
)
@click.option(
    "-j",
    "--jobs",
    type=int,
    required=True,
    show_default=True,
    help=(
        "The xxHash-64 hash value that represents the unique identifier for the process that manages this runtime. "
        "This is primarily used when calling this CLI on remote compute servers to ensure that only a single process "
        "can execute the CLI at a time."
    ),
)
def extract_camera_data(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path,
    jobs: int
) -> None:
    """Reads the compressed .npz log files stored in the raw_data directory of the target session and extracts all
    relevant behavior data stored in these files into the processed_data directory.

    This function is intended to run on the BioHPC server as part of the 'general' data processing pipeline. It is
    optimized to process all log files in parallel and extract the data stored inside the files into the behavior_data
    directory and camera_frames directory.
    """

    # Instantiates the SessionData instance for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )
