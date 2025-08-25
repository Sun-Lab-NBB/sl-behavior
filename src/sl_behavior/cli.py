"""This module stores the Command-Line Interfaces (CLIs) exposes by the library as part of the installation process."""

from pathlib import Path

import click
from sl_shared_assets import SessionData

from .camera import process_camera_timestamps
from .microcontrollers import process_microcontroller_data
from .runtime import process_runtime_data


@click.command()
@click.option(
    "-sp",
    "--session_path",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the session whose raw behavior log data needs to be extracted into .feather files.",
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
@click.option(
    "-id",
    "--manager_id",
    type=int,
    required=True,
    default=0,
    show_default=True,
    help=(
        "The xxHash-64 hash value that represents the unique identifier for the process that manages this runtime. "
        "This is primarily used when calling this CLI on remote compute servers to ensure that only a single process "
        "can execute the CLI at a time."
    ),
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
def extract_camera_data(
    session_path: Path,
    manager_id: int,
    processed_data_root: Path,
    jobs: int
) -> None:
    # Instantiates the SessionData instance for the processed session
    session_data = SessionData.load(
        session_path=session_path,
        processed_data_root=processed_data_root,
    )


def extract_log_data(
    session_data: SessionData, manager_id: int, parallel_workers: int = 7, update_manifest: bool = False
) -> None:
    """Reads the compressed .npz log files stored in the raw_data directory of the target session and extracts all
    relevant behavior data stored in these files into the processed_data directory.

    This function is intended to run on the BioHPC server as part of the 'general' data processing pipeline. It is
    optimized to process all log files in parallel and extract the data stored inside the files into the behavior_data
    directory and camera_frames directory.

    Args:
        session_data: The SessionData instance for the processed session.
        manager_id: The xxHash-64 hash-value that specifies the unique identifier of the manager process that
            manages the log processing runtime.
        parallel_workers: The number of CPU cores (workers) to use for processing the data in parallel. Note, this
            number should not exceed the number of available log files.
        update_manifest: Determines whether to update (regenerate) the project manifest file for the processed
            session's project. This should always be enabled when working with remote compute server(s) to ensure that
            the project manifest file contains the most actual snapshot of the project's state.
    """

    # Instantiates the ProcessingTracker instance for behavior log processing and configures the underlying tracker file
    # to indicate that the processing is ongoing. Note, this automatically invalidates any previous processing runtimes.
    tracker = get_processing_tracker(
        root=session_data.processed_data.processed_data_path, file_name=TrackerFileNames.BEHAVIOR
    )
    tracker.start(manager_id=manager_id)

    try:
        # Resolves the paths to the specific directories used during processing
        log_directory = session_data.raw_data.behavior_data_path
        behavior_data_directory = session_data.processed_data.behavior_data_path
        camera_data_directory = session_data.processed_data.camera_data_path

        # Should exist inside the raw data directory
        hardware_configuration_path = session_data.raw_data.hardware_state_path

        if session_data.acquisition_system not in _supported_acquisition_systems:
            message = (
                f"Unable to process behavior data for session '{session_data.session_name}' of "
                f"animal {session_data.animal_id} and project {session_data.project_name}. The input session was "
                f"acquired with an unsupported acquisition system: {session_data.acquisition_system}. Currently, "
                f"only sessions acquired using the following acquisition systems are supported: "
                f"{', '.join(_supported_acquisition_systems)}."
            )
            console.error(message=message, error=ValueError)

        if session_data.session_type not in _supported_session_types:
            message = (
                f"Unable to process behavior data for session '{session_data.session_name}' of "
                f"animal {session_data.animal_id} and project {session_data.project_name}. The input session is of an "
                f"unsupported type {session_data.session_type}. Currently, only the following session types are "
                f"supported: {', '.join(_supported_session_types)}."
            )
            console.error(message=message, error=ValueError)

        # Finds all .npz log files inside the input log file directory. Assumes there are no uncompressed log files.
        compressed_files: list[Path] = [file for file in log_directory.glob("*.npz")]

        # Loads the input MesoscopeHardwareState file to read the hardware parameters necessary to parse the data
        hardware_configuration: MesoscopeHardwareState = MesoscopeHardwareState.from_yaml(  # type: ignore
            file_path=hardware_configuration_path,
        )

        experiment_configuration: MesoscopeExperimentConfiguration | None = None
        if session_data.raw_data.experiment_configuration_path.exists():
            experiment_configuration = MesoscopeExperimentConfiguration.from_yaml(  # type: ignore
                file_path=session_data.raw_data.experiment_configuration_path
            )

        # If there are no compressed log files to process, returns immediately
        if len(compressed_files) == 0:
            return

        # Mesoscope VR Processing
        if session_data.acquisition_system == AcquisitionSystems.MESOSCOPE_VR:
            # Iterates over all compressed log files and processes them in-parallel
            with ProcessPoolExecutor(max_workers=parallel_workers) as executor:
                message = (
                    f"Processing behavior log files acquired with the Mesoscope-VR acquisition system during the "
                    f"session {session_data.session_name} of animal {session_data.animal_id} and project "
                    f"{session_data.project_name}..."
                )
                console.echo(message=message, level=LogLevel.INFO)

                futures = set()
                for file in compressed_files:
                    # Acquisition System log file. Currently, all valid runtimes generate log data, so this file is
                    # always parsed.
                    if file.stem == "1_log":
                        futures.add(
                            executor.submit(
                                _process_runtime_data,
                                file,
                                behavior_data_directory,
                                experiment_configuration,
                            )
                        )

                    # Face Camera timestamps
                    if file.stem == "51_log":
                        futures.add(
                            executor.submit(
                                _process_camera_timestamps,
                                file,
                                camera_data_directory.joinpath("face_camera_timestamps.feather"),
                            )
                        )

                    # Left Camera timestamps
                    if file.stem == "62_log":
                        futures.add(
                            executor.submit(
                                _process_camera_timestamps,
                                file,
                                camera_data_directory.joinpath("left_camera_timestamps.feather"),
                            )
                        )

                    # Right Camera timestamps
                    if file.stem == "73_log":
                        futures.add(
                            executor.submit(
                                _process_camera_timestamps,
                                file,
                                camera_data_directory.joinpath("right_camera_timestamps.feather"),
                            )
                        )

                    # Actor AMC module data
                    if file.stem == "101_log":
                        futures.add(
                            executor.submit(
                                _process_actor_data,
                                file,
                                behavior_data_directory,
                                hardware_configuration,
                            )
                        )

                    # Sensor AMC module data
                    if file.stem == "152_log":
                        futures.add(
                            executor.submit(
                                _process_sensor_data,
                                file,
                                behavior_data_directory,
                                hardware_configuration,
                            )
                        )

                    # Encoder AMC module data
                    if file.stem == "203_log":
                        futures.add(
                            executor.submit(
                                _process_encoder_data,
                                file,
                                behavior_data_directory,
                                hardware_configuration,
                            )
                        )

                # Displays a progress bar to track the parsing status if the function is called in the verbose mode.
                with tqdm(
                    total=len(futures),
                    desc=f"Processing log files",
                    unit="file",
                ) as pbar:
                    for future in as_completed(futures):
                        # Propagates any exceptions from the worker processes
                        future.result()
                        pbar.update(1)

                    # Configures the tracker to indicate that the processing runtime completed successfully
                    tracker.stop(manager_id=manager_id)

        # Aborts with an error if processing logic for the target acquisition system is not implemented
        else:
            message = (
                f"Behavior data processing logic for the acquisition system {session_data.acquisition_system} "
                f"is not implemented. Unable to process the session {session_data.session_name} of "
                f"animal {session_data.animal_id} and project {session_data.project_name}."
            )
            console.error(message=message, error=NotImplementedError)

        console.echo(message="Log processing: Complete.", level=LogLevel.SUCCESS)

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the processing runtime encountered an error. Configures the tracker to indicate that this
        # runtime finished with an error to prevent deadlocking future runtime calls.
        if tracker.is_running:
            tracker.error(manager_id=manager_id)

        # If the runtime is configured to generate the project manifest file, attempts to generate and overwrite the
        # existing manifest file for the target project.
        if update_manifest:
            # All sessions are stored under root/project/animal/session. SessionData exposes paths to either raw_data or
            # processed_data subdirectories under the root session directory on each volume. Indexing parents of
            # SessionData paths gives the project-specific directory at index 2 and the root for that directory at
            # index 3.
            raw_directory = session_data.raw_data.raw_data_path.parents[2]
            processed_directory = session_data.processed_data.processed_data_path.parents[3]

            # Generates the manifest file inside the root raw data project directory
            generate_project_manifest(
                raw_project_directory=raw_directory,
                processed_data_root=processed_directory,
                output_directory=raw_directory,
            )
