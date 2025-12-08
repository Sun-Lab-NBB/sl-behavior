"""This module provides the Command-Line Interfaces (CLIs) for processing behavior data acquired in the Sun lab. Most
of these CLIs are intended to run on the remote compute server and should not be used by end-users directly.
"""

from pathlib import Path

import click

from .camera import process_camera_timestamps
from .runtime import process_runtime_data
from .microcontrollers import process_microcontroller_data

# Ensures that displayed CLICK help messages are formatted according to the lab standard.
CONTEXT_SETTINGS = {"max_content_width": 120}


@click.group("behavior", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-sp",
    "--session-path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help=(
        "The absolute path to the session's root data directory to process. This directory must contain the 'raw_data' "
        "subdirectory."
    ),
)
@click.option(
    "-id",
    "--job-id",
    type=str,
    required=True,
    help="The unique hexadecimal identifier for this processing job.",
)
@click.pass_context
def behavior(
    ctx: click.Context,
    session_path: Path,
    job_id: str,
) -> None:
    """This Command-Line Interface (CLI) group allows processing behavior data acquired in the Sun lab.

    This CLI group is intended to run on the Sun lab remote compute server(s) and should not be called by the end-user
    directly. Instead, commands from this CLI are designed to be accessed through the bindings in the sl-forgery
    library.
    """
    ctx.ensure_object(dict)
    ctx.obj["session_path"] = session_path
    ctx.obj["job_id"] = job_id


@behavior.command("camera")
@click.option(
    "-l",
    "--log-id",
    type=click.Choice(["51", "62", "73"]),
    required=True,
    help="The camera log ID: 51 (face), 62 (body), or 73 (right).",
)
@click.pass_context
def extract_camera_data(ctx: click.Context, log_id: str) -> None:
    """Reads the target video camera log file and extracts the timestamps for all acquired camera frames as an
    uncompressed .feather file.
    """
    session_path = ctx.obj["session_path"]
    job_id = ctx.obj["job_id"]

    process_camera_timestamps(
        session_path=session_path,
        log_id=int(log_id),
        job_id=job_id,
    )


@behavior.command("runtime")
@click.pass_context
def extract_runtime_data(ctx: click.Context) -> None:
    """Reads the data acquisition system log file for the target session and extracts the runtime (task) and data
    acquisition system configuration data as multiple uncompressed .feather files.
    """
    session_path = ctx.obj["session_path"]
    job_id = ctx.obj["job_id"]

    process_runtime_data(
        session_path=session_path,
        job_id=job_id,
    )


@behavior.command("microcontroller")
@click.option(
    "-l",
    "--log-id",
    type=click.Choice(["101", "152", "203"]),
    required=True,
    help="The microcontroller log ID: 101 (actor), 152 (sensor), or 203 (encoder).",
)
@click.pass_context
def extract_microcontroller_data(ctx: click.Context, log_id: str) -> None:
    """Reads the target microcontroller log file and extracts the data recorded by all hardware modules managed by that
    microcontroller as multiple uncompressed .feather files.
    """
    session_path = ctx.obj["session_path"]
    job_id = ctx.obj["job_id"]

    process_microcontroller_data(
        session_path=session_path,
        log_id=int(log_id),
        job_id=job_id,
    )
