"""This module provides the Command-Line Interfaces (CLIs) for processing behavior data acquired in the Sun lab. Most
of these CLIs are intended to run on the remote compute server and should not be used by end-users directly."""

from typing import Any
from pathlib import Path

import click

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
    "-j",
    "--jobs",
    type=int,
    required=True,
    show_default=True,
    help=(
        "The total number of individual processing jobs to be executed as part of the behavior processing pipeline. "
        "This value is used to track when the processing pipeline as a whole finishes its runtime."
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
    "-l",
    "--log-id",
    type=int,
    default=1,
    required=True,
    show_default=True,
    help="The integer ID used in the name of the log file that stores the data to be processed.",
)
@click.option(
    "-r",
    "--reset-tracker",
    is_flag=True,
    required=False,
    help=(
        "Determines whether to forcibly reset the tracker file for the behavior processing pipeline before runtime. "
        "This flag should only be used in exceptional cases to recover from improper runtime terminations."
    ),
)
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

    ctx.ensure_object(dict)
    ctx.obj["session_path"] = session_path
    ctx.obj["processed_data_root"] = processed_data_root
    ctx.obj["manager_id"] = manager_id
    ctx.obj["log_id"] = log_id
    ctx.obj["reset_tracker"] = reset_tracker
    ctx.obj["jobs"] = jobs


@behavior.command("camera")
@click.pass_context
def extract_camera_data(
    ctx: Any,
) -> None:
    """Reads the target video camera log file and extracts the timestamps for all acquired camera frames as an
    uncompressed .feather file.
    """

    # Extracts shared parameters from context
    session_path = ctx.obj["session_path"]
    processed_data_root = ctx.obj["processed_data_root"]
    manager_id = ctx.obj["manager_id"]
    reset_tracker = ctx.obj["reset_tracker"]
    jobs = ctx.obj["jobs"]
    log_id = ctx.obj["log_id"]

    process_camera_timestamps(
        session_path=session_path,
        log_id=log_id,
        manager_id=manager_id,
        job_count=jobs,
        processed_data_root=processed_data_root,
        reset_tracker=reset_tracker,
    )


@behavior.command("runtime")
@click.pass_context
def extract_runtime_data(
    ctx: Any,
) -> None:
    """Reads the data acquisition system log file for the target session and extracts the runtime (task) and data
    acquisition system configuration data as multiple uncompressed .feather files.
    """

    # Extracts shared parameters from context
    session_path = ctx.obj["session_path"]
    processed_data_root = ctx.obj["processed_data_root"]
    manager_id = ctx.obj["manager_id"]
    reset_tracker = ctx.obj["reset_tracker"]
    jobs = ctx.obj["jobs"]

    process_runtime_data(
        session_path=session_path,
        manager_id=manager_id,
        job_count=jobs,
        processed_data_root=processed_data_root,
        reset_tracker=reset_tracker,
    )


@behavior.command("microcontroller")
@click.pass_context
def extract_microcontroller_data(
    ctx: Any,
) -> None:
    """Reads the target microcontroller log file and extracts the data recorded by all hardware modules managed by that
    microcontroller as multiple uncompressed .feather files.
    """

    # Extracts shared parameters from context
    session_path = ctx.obj["session_path"]
    processed_data_root = ctx.obj["processed_data_root"]
    manager_id = ctx.obj["manager_id"]
    reset_tracker = ctx.obj["reset_tracker"]
    jobs = ctx.obj["jobs"]
    log_id = ctx.obj["log_id"]

    process_microcontroller_data(
        session_path=session_path,
        log_id=log_id,
        manager_id=manager_id,
        job_count=jobs,
        processed_data_root=processed_data_root,
        reset_tracker=reset_tracker,
    )
