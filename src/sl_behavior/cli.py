"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from sl_shared_assets import SessionData

from .legacy import extract_gimbl_data
from .log_processing import extract_log_data


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session whose raw behavior log data needs to be extracted into .feather files.",
)
@click.option(
    "-pdr",
    "--processed_data_root",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=False,
    help=(
        "The absolute path to the directory where processed data from all projects is stored on the machine that runs "
        "this command. This argument is used when calling the CLI on the BioHPC server, which uses different data "
        "volumes for raw and processed data. Note, the input path must point to the root directory, as it will be "
        "automatically modified to include the project name, the animal id, and the session ID."
    ),
)
@click.option(
    "-l",
    "--legacy",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether the processed session is a modern Sun lab session or a 'legacy' Tyche project session. Do "
        "not provide this flag unless you are working with 'ascended' Tyche data."
    ),
)
def extract_behavior_data(session_path: str, processed_data_root: Path, legacy: bool) -> None:
    # Instantiates the SessionData instance for the processed session
    session = Path(session_path)
    session_data = SessionData.load(session_path=session, processed_data_root=processed_data_root)

    # If the processed session is a modern Sun lab session, extracts session's behavior data from multiple .npz log
    # files
    if not legacy:
        extract_log_data(session_data=session_data)
    else:
        # Otherwise, extracts session's behavior data from the single GIMBL.json log file
        extract_gimbl_data(session_data=session_data)
