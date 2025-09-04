from typing import Any
from pathlib import Path

import click
from _typeshed import Incomplete

from .camera import process_camera_timestamps as process_camera_timestamps
from .runtime import process_runtime_data as process_runtime_data
from .microcontrollers import process_microcontroller_data as process_microcontroller_data

CONTEXT_SETTINGS: Incomplete

@click.pass_context
def behavior(
    ctx: Any,
    session_path: Path,
    processed_data_root: Path | None,
    jobs: int,
    manager_id: int,
    log_id: int,
    reset_tracker: bool,
) -> None:
    """This Command-Line Interface (CLI) group allows processing behavior data acquired in the Sun lab.

    This CLI group is intended to run on the Sun lab remote compute server(s) and should not be called by the end-user
    directly. Instead, commands from this CLI are designed to be accessed through the bindings in the sl-forgery
    library.
    """

@click.pass_context
def extract_camera_data(ctx: Any) -> None:
    """Reads the target video camera log file and extracts the timestamps for all acquired camera frames as an
    uncompressed .feather file.
    """

@click.pass_context
def extract_runtime_data(ctx: Any) -> None:
    """Reads the data acquisition system log file for the target session and extracts the runtime (task) and data
    acquisition system configuration data as multiple uncompressed .feather files.
    """

@click.pass_context
def extract_microcontroller_data(ctx: Any) -> None:
    """Reads the target microcontroller log file and extracts the data recorded by all hardware modules managed by that
    microcontroller as multiple uncompressed .feather files.
    """
