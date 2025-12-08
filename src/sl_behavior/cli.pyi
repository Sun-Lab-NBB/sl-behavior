from pathlib import Path

import click
from _typeshed import Incomplete

from .camera import process_camera_timestamps as process_camera_timestamps
from .runtime import process_runtime_data as process_runtime_data
from .microcontrollers import process_microcontroller_data as process_microcontroller_data

CONTEXT_SETTINGS: Incomplete

@click.pass_context
def behavior(ctx: click.Context, session_path: Path, job_id: str) -> None: ...
@click.pass_context
def extract_camera_data(ctx: click.Context, log_id: str) -> None: ...
@click.pass_context
def extract_runtime_data(ctx: click.Context) -> None: ...
@click.pass_context
def extract_microcontroller_data(ctx: click.Context, log_id: str) -> None: ...
