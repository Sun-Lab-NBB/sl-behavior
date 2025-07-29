"""This module provides the high-level GIMBL .JSON log parsing logic. The logic from this module reads the .JSON file
and parses it as multiple .feather files expected by the modern Sun lab data processing pipelines."""

import os
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from sl_shared_assets import SessionData, ProcessingTracker
from sl_shared_assets.tools import generate_project_manifest
from ataraxis_base_utilities import LogLevel, console

from .parse import (
    parse_gimbl_log,
    parse_trial_info,
    parse_period_info,
    parse_session_events,
)

# Default cue table (immutable so it can be re‑used across calls)
DEFAULT_CUE_DEFINITIONS: tuple[dict[str, int | str], ...] = (
    {"name": "Gray_60cm", "position_start": 0, "position_end": 60},
    {"name": "Indicator", "position_start": 60, "position_end": 100},
    {"name": "Gray_30cm", "position_start": 100, "position_end": 130},
    {"name": "R1", "position_start": 130, "position_end": 150},
    {"name": "Gray_30cm", "position_start": 150, "position_end": 180},
    {"name": "R2", "position_start": 180, "position_end": 200},
    {"name": "Gray_30cm", "position_start": 200, "position_end": 230},
    {"name": "Teleportation", "position_start": 230, "position_end": 231},
)


def _extract_cue_changes(
    path: pd.DataFrame,
    *,
    cue_definitions: Sequence[Mapping[str, int | str]] = DEFAULT_CUE_DEFINITIONS,
    position_col: str = "position",
    time_col: str = "time_us",
) -> pd.DataFrame:
    """Generates that stores the sequence of wall cues experienced by the animal while running the session alongside
    the timestamp for each wall cue transition.

    Args:
        path: The Pandas DataFrame that stores the parsed session path information and contains at least 'position_col'
            and 'time_col'.
        cue_definitions: The ordered list or tuple of mappings with keys 'name', 'position_start', and 'position_end'.
            The default value of this argument corresponds to the standard 2‑AC track used in the Tyche project.
        position_col: The name of the column in 'path' that stores the linearized position values.
        time_col: The name of the column in 'path' that stores monotonic time stamps (in µs since UTC epoch onset).

    Returns:
        The Pandas DataFrame with columns 'time_us', 'vr_cue' and 'cue_name'.
    """
    # Ensures that the input path data contains the required information
    missing = {c for c in (position_col, time_col) if c not in path.columns}
    if missing:
        message = (
            f"Unbale to extract the wall cue changes that correspond to the animal's motion along the linear track. "
            f"The Pandas DataFrame passed as the 'path' argument is missing required column(s): {missing}."
        )
        console.error(message=message, error=KeyError)

    # Reads the input cue table and ensures it contains the required information.
    cues_df = pd.DataFrame(cue_definitions, copy=False)
    if not {"name", "position_start", "position_end"}.issubset(cues_df.columns):
        message = (
            "Unbale to extract the wall cue changes that correspond to the animal's motion along the linear track. "
            "The dictionary passed as the 'cue_definitions' argument must supply the 'name', 'position_start' and "
            "'position_end' keys, but at least one expected key is missing."
        )
        console.error(message=message, error=ValueError)

    # Defines stable integer labels for faster look‑ups
    cues_df["vr_cue"] = cues_df["name"].astype("category").cat.codes

    # Bins the distance traveled by the animal to generate the sequence of wall cues observed by the animal at each
    # distance point.
    positions = path[position_col].to_numpy(copy=False)
    bin_edges = cues_df["position_start"].to_numpy(copy=False)
    cue_bins = np.digitize(positions, bin_edges, right=False)
    bin_changes = np.diff(cue_bins)

    change_idx = np.where(bin_changes != 0)[0] + 1
    change_idx = np.insert(change_idx, 0, 0)

    # Assembles the output cue DataFrame.
    return pd.DataFrame(
        {
            "time_us": path[time_col].iloc[change_idx].to_numpy(),
            "vr_cue": cues_df["vr_cue"].iloc[cue_bins[change_idx] - 1].values,
            "cue_name": cues_df["name"].iloc[cue_bins[change_idx] - 1].values,
        }
    ).reset_index(drop=True)


def extract_gimbl_data(session_data: SessionData, update_manifest: bool = False) -> None:
    """Reads and exports the data stored in the GIMBL .JSOn file to individual .feather files.

    This is a service function designed to process the legacy data from the Tyche dataset. It should not be used with
    modern Sun lab data and instead is purpose-built for reanalyzing the legacy Tyche dataset. Do not call this function
    unless you know what you are doing.

    Args:
        session_data: The SessionData instance for the session whose legacy log data needs to be processed.
        update_manifest: Determines whether to update (regenerate) the project manifest file for the processed
            session's project. This should always be enabled when working with remote compute server(s) to ensure that
            the project manifest file contains the most actual snapshot of the project's state.
    """

    # Instantiates the ProcessingTracker instance for behavior log processing and configures the underlying tracker file
    # to indicate that the processing is ongoing. Note, this automatically invalidates any previous processing runtimes.
    tracker = ProcessingTracker(file_path=session_data.processed_data.behavior_processing_tracker_path)
    tracker.start()

    try:
        # Resolves input and output directory paths using SessionData
        input_directory = session_data.raw_data.behavior_data_path
        output_directory = session_data.processed_data.behavior_data_path

        if session_data.project_name != "Tyche":
            message = (
                f"Unable to process behavior data for legacy session '{session_data.session_name}' of "
                f"animal {session_data.animal_id}. The input session belong to the project {session_data.project_name} "
                f"instead of the expected 'Tyche' project. Currently, legacy data parsing only supports sessions "
                f"acquired under the Tyche project."
            )
            console.error(message=message, error=ValueError)

        console.echo(f"Processing legacy GIMBL log file...", level=LogLevel.INFO)

        # A valid legacy session should contain a single .json file in the raw 'behavior_data' subdirectory. Otherwise,
        # the function raises an error.
        json_files = [file for file in input_directory.glob("*.json")]
        if len(json_files) != 1:
            message = (
                f"Unable to extract the legacy behavior data from the GIMBL .JSON log file. Expected a single .json "
                f"file in the raw 'behavior_data' subdirectory of the processed session, but instead encountered "
                f"{len(json_files)} files."
            )
            console.error(message=message, error=FileNotFoundError)
            raise FileNotFoundError(message)  # Fallback to appease mypy
        else:
            log_file_path = json_files[0]

        # Loads and parses the log data into a GimblData object and a DataFrame.
        logs_df, data = parse_gimbl_log(log_file_path)

        # Mesoscope frame timestamp data.
        if hasattr(data, "frames") and isinstance(data.frames, pd.DataFrame):
            data.frames.to_feather(os.path.join(output_directory, "mesoscope_frame_data.feather"))

        # Linear position data
        if hasattr(data, "position"):
            if hasattr(data.position, "time") and isinstance(data.position.time, pd.DataFrame):
                data.position.time.to_feather(os.path.join(output_directory, "position_time.feather"))
            if hasattr(data.position, "frame") and isinstance(data.position.frame, pd.DataFrame):
                data.position.frame.to_feather(os.path.join(output_directory, "position_frame_avg.feather"))

        # Movement (Encoder) data. Includes some additional fields unique to how Tyche project logged the data.
        if hasattr(data, "path"):
            if hasattr(data.path, "time") and isinstance(data.path.time, pd.DataFrame):
                data.path.time.to_feather(os.path.join(output_directory, "path_time.feather"))

                # encoder data
                all_pos = data.path.time.position.to_numpy()
                all_pos = np.clip(all_pos, 0, 230)
                all_pos_diff = np.diff(all_pos, prepend=0)
                all_pos_diff[all_pos_diff < 0] = 0
                all_pos_csum = np.cumsum(all_pos_diff)

                encoder_data = pd.DataFrame(
                    {
                        "time_us": data.path.time.time_us.to_numpy(),
                        "traveled_distance_cm": all_pos_csum,
                    }
                )

                encoder_data.to_feather(os.path.join(output_directory, "encoder_data.feather"))

                cue_data = _extract_cue_changes(data.path.time, cue_definitions=DEFAULT_CUE_DEFINITIONS)
                cue_data.to_feather(os.path.join(output_directory, "cue_data.feather"))

            if hasattr(data.path, "frame") and isinstance(data.path.frame, pd.DataFrame):
                data.path.frame.to_feather(os.path.join(output_directory, "path_frame_avg.feather"))

        # Camera frame data
        if hasattr(data, "camera") and isinstance(data.camera, pd.DataFrame):
            data.camera.to_feather(os.path.join(output_directory, "face_camera_timestamps.feather"))

        # Reward data
        if hasattr(data, "reward") and isinstance(data.reward, pd.DataFrame):
            data.reward.to_feather(os.path.join(output_directory, "valve_data.feather"))

        # Lick data
        if hasattr(data, "lick") and isinstance(data.lick, pd.DataFrame):
            data.lick.to_feather(os.path.join(output_directory, "lick_data.feather"))

        # Idle period data. Note, Idle periods are not teleport or darkness periods. Idle periods are voluntary and in
        # early animals a 'punishment' sound was used to force the animal to continue running. The sound was deprecated
        # early into the project.
        if hasattr(data, "idle") and hasattr(data.idle, "sound") and isinstance(data.idle.sound, pd.DataFrame):
            data.idle.sound.to_feather(os.path.join(output_directory, "idle_sound.feather"))

        # Parses linear position data
        if hasattr(data, "linear_controller"):
            if hasattr(data.linear_controller, "settings") and isinstance(
                data.linear_controller.settings, pd.DataFrame
            ):
                data.linear_controller.settings.to_feather(
                    os.path.join(output_directory, "linear_controller_settings.feather")
                )
            if hasattr(data.linear_controller, "time") and isinstance(data.linear_controller.time, pd.DataFrame):
                data.linear_controller.time.to_feather(os.path.join(output_directory, "linear_controller_time.feather"))
            if hasattr(data.linear_controller, "frame") and isinstance(data.linear_controller.frame, pd.DataFrame):
                data.linear_controller.frame.to_feather(
                    os.path.join(output_directory, "linear_controller_frame_avg.feather")
                )

        # Spherical controller data. It is highly likely that this section will never be used, as this code is only
        # intended to parse the Tyche project data, which used the linear controller.
        if hasattr(data, "spherical_controller"):
            if hasattr(data, "spherical_controller_settings") and isinstance(
                data.spherical_controller_settings, pd.DataFrame
            ):
                data.spherical_controller_settings.to_feather(
                    os.path.join(output_directory, "spherical_controller_settings.feather")
                )
            if hasattr(data.spherical_controller, "time") and isinstance(data.spherical_controller.time, pd.DataFrame):
                data.spherical_controller.time.to_feather(
                    os.path.join(output_directory, "spherical_controller_time.feather")
                )
            if hasattr(data.spherical_controller, "frame") and isinstance(
                data.spherical_controller.frame, pd.DataFrame
            ):
                data.spherical_controller.frame.to_feather(
                    os.path.join(output_directory, "spherical_controller_frame_avg.feather")
                )

        # Trial information.
        trial_data = parse_trial_info(logs_df)
        trial_data.to_feather(os.path.join(output_directory, "trial_data.feather"))

        # Session information.
        filtered_events = parse_session_events(logs_df)
        filtered_events.to_feather(os.path.join(output_directory, "session_data.feather"))

        # Experiment phase / state information.
        period_data = parse_period_info(logs_df)
        period_data.to_feather(os.path.join(output_directory, "period_data.feather"))

        # Configures the tracker to indicate that the processing runtime completed successfully
        tracker.stop()

        console.echo(f"Legacy GIMBL log file: Processed.", level=LogLevel.SUCCESS)

    finally:
        # If the code reaches this section while the tracker indicates that the processing is still running,
        # this means that the verification runtime encountered an error. Configures the tracker to indicate that this
        # runtime finished with an error to prevent deadlocking the runtime.
        if tracker.is_running:
            tracker.error()

        # If the runtime is configured to generate the project manifest file, attempts to generate and overwrite the
        # existing manifest file for the target project.
        if update_manifest:
            # All sessions are stored under root/project/animal/session. SessionData exposes paths to either raw_data or
            # processed_data subdirectories under the root session directory on each volume. Indexing parents of
            # SessionData paths gives project-specific directory at index 2 and the root for that directory at index 3.
            raw_directory = session_data.raw_data.raw_data_path.parents[2]
            processed_directory = session_data.processed_data.processed_data_path.parents[3]

            # Generates the manifest file inside the root raw data project directory
            generate_project_manifest(
                raw_project_directory=raw_directory,
                processed_data_root=processed_directory,
                output_directory=raw_directory,
            )
