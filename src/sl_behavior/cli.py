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
        "automatically modified to include the project name, the animal id, and the session ID. Do not provide this "
        "argument if processed and raw data roots are the same."
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
@click.option(
    "-c",
    "--create_processed_directories",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Determines whether to create the processed data hierarchy. Typically, this flag only needs to be enabled when "
        "this command is called outside of the typical data processing pipeline used in the Sun lab. Usually, "
        "processed data directories are created at an earlier stage of data processing, if it is carried out on the "
        "remote compute server."
    ),
)
@click.option(
    "-um",
    "--update_manifest",
    is_flag=True,
    help=(
        "Determines whether to (re)generate the manifest file for the processed session's project. This flag "
        "should always be enabled when this CLI is executed on the remote compute server(s) to ensure that the "
        "manifest file always reflects the most actual state of each project."
    ),
)
def extract_behavior_data(
    session_path: Path,
    processed_data_root: Path,
    legacy: bool,
    create_processed_directories: bool,
    update_manifest: bool,
) -> None:
    # Instantiates the SessionData instance for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
        make_processed_data_directory=create_processed_directories,
    )

    # If the processed session is a modern Sun lab session, extracts session's behavior data from multiple .npz log
    # files
    if not legacy:
        extract_log_data(session_data=session_data, update_manifest=update_manifest)
    else:
        # Otherwise, extracts session's behavior data from the single GIMBL.json log file
        extract_gimbl_data(session_data=session_data, update_manifest=update_manifest)
