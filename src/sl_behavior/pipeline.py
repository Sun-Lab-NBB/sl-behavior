"""This module provides the centralized pipeline for processing behavior data acquired in the Sun lab. The pipeline
supports both local and remote processing modes.
"""

from enum import StrEnum
from pathlib import Path  # noqa: TC003

from sl_shared_assets import SessionData, ProcessingTracker, ProcessingTrackers
from ataraxis_base_utilities import LogLevel, console

from .camera import CameraLogIds, process_camera_timestamps
from .runtime import process_runtime_data
from .microcontrollers import MicrocontrollerLogIds, process_microcontroller_data


class BehaviorJobNames(StrEnum):
    """Defines the job names used by the behavior data processing pipeline."""

    RUNTIME = "runtime_processing"
    """The name for the runtime data processing job."""
    FACE_CAMERA = "face_camera_processing"
    """The name for the face camera timestamp processing job."""
    BODY_CAMERA = "body_camera_processing"
    """The name for the body camera timestamp processing job."""
    ACTOR_MICROCONTROLLER = "actor_microcontroller_processing"
    """The name for the Actor microcontroller data processing job."""
    SENSOR_MICROCONTROLLER = "sensor_microcontroller_processing"
    """The name for the Sensor microcontroller data processing job."""
    ENCODER_MICROCONTROLLER = "encoder_microcontroller_processing"
    """The name for the Encoder microcontroller data processing job."""


def _resolve_available_jobs(session_path: Path) -> dict[str, bool]:
    """Detects which processing jobs can run on the session's data based on existing log files.

    Args:
        session_path: The path to the session's data directory.

    Returns:
        A dictionary mapping job names to boolean values indicating whether the corresponding log file exists.
    """
    session = SessionData.load(session_path=session_path)
    behavior_data_path = session.raw_data.behavior_data_path

    # Checks for each log file and determines which jobs are available.
    available_jobs: dict[str, bool] = {
        BehaviorJobNames.RUNTIME: behavior_data_path.joinpath("1_log.npz").exists(),
        BehaviorJobNames.FACE_CAMERA: behavior_data_path.joinpath(f"{CameraLogIds.FACE}_log.npz").exists(),
        BehaviorJobNames.BODY_CAMERA: behavior_data_path.joinpath(f"{CameraLogIds.BODY}_log.npz").exists(),
        BehaviorJobNames.ACTOR_MICROCONTROLLER: behavior_data_path.joinpath(
            f"{MicrocontrollerLogIds.ACTOR}_log.npz"
        ).exists(),
        BehaviorJobNames.SENSOR_MICROCONTROLLER: behavior_data_path.joinpath(
            f"{MicrocontrollerLogIds.SENSOR}_log.npz"
        ).exists(),
        BehaviorJobNames.ENCODER_MICROCONTROLLER: behavior_data_path.joinpath(
            f"{MicrocontrollerLogIds.ENCODER}_log.npz"
        ).exists(),
    }

    return available_jobs


def _generate_job_ids(session_path: Path, job_names: list[str]) -> dict[str, str]:
    """Generates unique processing job identifiers for the specified jobs.

    Args:
        session_path: The path to the session's data directory.
        job_names: The list of job names for which to generate the IDs.

    Returns:
        A dictionary mapping job names to their generated job IDs.
    """
    job_ids: dict[str, str] = {}
    for job_name in job_names:
        job_ids[job_name] = ProcessingTracker.generate_job_id(session_path=session_path, job_name=job_name)
    return job_ids


def _initialize_processing_tracker(
    session_path: Path,
    job_names: list[str],
) -> dict[str, str]:
    """Initializes the processing tracker file using the requested job IDs.

    Notes:
        This function is used to process the data in the 'local' processing mode. During remote data processing, the
        tracker file is pre-generated before submitting the processing jobs to the remote compute server.

    Args:
        session_path: The path to the session's data directory.
        job_names: The names for the processing jobs to track.

    Returns:
        A dictionary mapping job names to their generated job IDs.
    """
    session = SessionData.load(session_path=session_path)

    # Initializes the processing tracker for this pipeline.
    tracker = ProcessingTracker(
        file_path=session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)
    )

    # Generates job IDs for each requested job.
    job_ids = _generate_job_ids(session_path=session_path, job_names=job_names)

    # Initializes all jobs in the tracker file.
    tracker.initialize_jobs(job_ids=list(job_ids.values()))

    return job_ids


def process_session(
    session_path: Path,
    job_id: str | None = None,
    *,
    process_runtime: bool = False,
    process_face_camera: bool = False,
    process_body_camera: bool = False,
    process_actor_microcontroller: bool = False,
    process_sensor_microcontroller: bool = False,
    process_encoder_microcontroller: bool = False,
    workers: int = -1,
) -> None:
    """Processes the requested behavior data log of the target data acquisition session.

    Args:
        session_path: The path to the session's data directory.
        job_id: The unique hexadecimal identifier for the processing job to execute. If provided, only the job
            matching this ID is executed. If not provided, all requested jobs are run sequentially with automatic
            tracker management. Typically, this mode of job definition is used when running the processing on the
            remote compute server via the bindings in the sl-forgery library.
        process_runtime: Determines whether to process the session runtime data.
        process_face_camera: Determines whether to process the face camera timestamps.
        process_body_camera: Determines whether to process the body camera timestamps.
        process_actor_microcontroller: Determines whether to process the Actor microcontroller data.
        process_sensor_microcontroller: Determines whether to process the Sensor microcontroller data.
        process_encoder_microcontroller: Determines whether to process the Encoder microcontroller data.
        workers: The number of worker processes to use for parallel processing. Setting this to a value less than 1
            uses all available CPU cores. Setting this to 1 conducts processing sequentially.
    """
    # Remote mode. If job_id is provided, attempts to run the requested processing job and raises an error if the
    # job cannot be executed.
    if job_id is not None:
        _run_single_job(session_path=session_path, job_id=job_id, workers=workers)
        return

    # Local mode: Generates job IDs, creates a local tracker file, and runs the requested jobs.

    # Resolves which jobs are available based on existing log files.
    available_jobs = _resolve_available_jobs(session_path=session_path)

    # Maps job names to their requested flags.
    requested_jobs: dict[str, bool] = {
        BehaviorJobNames.RUNTIME: process_runtime,
        BehaviorJobNames.FACE_CAMERA: process_face_camera,
        BehaviorJobNames.BODY_CAMERA: process_body_camera,
        BehaviorJobNames.ACTOR_MICROCONTROLLER: process_actor_microcontroller,
        BehaviorJobNames.SENSOR_MICROCONTROLLER: process_sensor_microcontroller,
        BehaviorJobNames.ENCODER_MICROCONTROLLER: process_encoder_microcontroller,
    }

    # If all requested job flags are False, treats them as all True (process all available jobs).
    if not any(requested_jobs.values()):
        requested_jobs = dict.fromkeys(requested_jobs, True)

    # Determines which jobs to run (requested AND available).
    jobs_to_run = [job_name for job_name, requested in requested_jobs.items() if requested and available_jobs[job_name]]

    # Initializes the tracker and runs all requested jobs sequentially.
    console.echo(message=f"Initializing processing tracker for {len(jobs_to_run)} job(s)...")
    job_ids = _initialize_processing_tracker(session_path=session_path, job_names=jobs_to_run)

    # Runs each job sequentially. If a job fails, _run_job_by_name marks it as failed and raises an exception,
    # aborting further processing. Jobs remaining in standby are handled by sl-forgery.
    for job_name in jobs_to_run:
        current_job_id = job_ids[job_name]
        console.echo(message=f"Running job: {job_name} (ID: {current_job_id})...")
        _run_job_by_name(session_path=session_path, job_name=job_name, job_id=current_job_id, workers=workers)

    console.echo(message="All processing jobs completed successfully.", level=LogLevel.SUCCESS)


def _run_single_job(
    session_path: Path,
    job_id: str,
    workers: int,
) -> None:
    """Runs the requested job identified by the input job_id.

    This function generates all possible job IDs, finds which job matches the provided job_id, and executes the
    corresponding processing pipeline.

    Args:
        session_path: The path to the session's data directory.
        job_id: The unique hexadecimal identifier for the processing job to run.
        workers: The number of worker processes to use for parallel processing.

    Raises:
        ValueError: If the input job_id does not match any processing jobs supported by the processed session's data.
    """
    # Loads the tracker for marking the job as failed if an error occurs before _run_job_by_name is called.
    session = SessionData.load(session_path=session_path)
    tracker = ProcessingTracker(
        file_path=session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)
    )

    # Generates all possible job IDs and creates a reverse lookup map.
    all_job_ids = _generate_job_ids(session_path=session_path, job_names=list(BehaviorJobNames))
    id_to_name: dict[str, str] = {job_id_val: name for name, job_id_val in all_job_ids.items()}

    # Finds the job name that matches the provided job_id.
    if job_id not in id_to_name:
        # Marks the job as failed before raising the error.
        tracker.fail_job(job_id=job_id)
        message = (
            f"Unable to execute the requested job with ID '{job_id}'. The input identifier does not match any "
            f"jobs available for this session. Use one of the valid job IDs: {list(all_job_ids.values())}."
        )
        console.error(message=message, error=ValueError)

    job_name = id_to_name[job_id]

    # Runs the identified job. Note: _run_job_by_name handles tracker updates for success/failure internally.
    _run_job_by_name(session_path=session_path, job_name=job_name, job_id=job_id, workers=workers)


def _run_job_by_name(
    session_path: Path,
    job_name: str,
    job_id: str,
    workers: int,
) -> None:
    """Runs the requested processing job identified by the input job name.

    Args:
        session_path: The path to the session's data directory.
        job_name: The name of the job to run.
        job_id: The unique hexadecimal identifier for this processing job.
        workers: The number of worker processes to use for parallel processing.

    Raises:
        ValueError: If the job_name is not recognized.
    """
    # Loads the session data and initializes the processing tracker.
    session = SessionData.load(session_path=session_path)
    tracker = ProcessingTracker(
        file_path=session.tracking_data.tracking_data_path.joinpath(ProcessingTrackers.BEHAVIOR)
    )

    # Marks the job as running.
    tracker.start_job(job_id=job_id)

    try:
        if job_name == BehaviorJobNames.RUNTIME:
            process_runtime_data(session_path=session_path)

        elif job_name == BehaviorJobNames.FACE_CAMERA:
            process_camera_timestamps(session_path=session_path, log_id=CameraLogIds.FACE, workers=workers)

        elif job_name == BehaviorJobNames.BODY_CAMERA:
            process_camera_timestamps(session_path=session_path, log_id=CameraLogIds.BODY, workers=workers)

        elif job_name == BehaviorJobNames.ACTOR_MICROCONTROLLER:
            process_microcontroller_data(session_path=session_path, log_id=MicrocontrollerLogIds.ACTOR, workers=workers)

        elif job_name == BehaviorJobNames.SENSOR_MICROCONTROLLER:
            process_microcontroller_data(
                session_path=session_path, log_id=MicrocontrollerLogIds.SENSOR, workers=workers
            )

        elif job_name == BehaviorJobNames.ENCODER_MICROCONTROLLER:
            process_microcontroller_data(
                session_path=session_path, log_id=MicrocontrollerLogIds.ENCODER, workers=workers
            )

        else:
            message = (
                f"Unable to execute the requested job {job_name} with ID '{job_id}'. The input job name is not "
                f"recognized. Use one of the valid Job names: {list(BehaviorJobNames)}."
            )
            console.error(message=message, error=ValueError)

        # Marks the job as successfully completed.
        tracker.complete_job(job_id=job_id)

    except Exception:
        tracker.fail_job(job_id=job_id)
        raise
