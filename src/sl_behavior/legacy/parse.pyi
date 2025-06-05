from pathlib import Path

import pandas as pd

from .data import (
    GimblData as GimblData,
    FieldTypes as FieldTypes,
)
from .transform import (
    assign_frame_info as assign_frame_info,
    convert_lick_data as convert_lick_data,
    convert_reward_data as convert_reward_data,
    forward_fill_missing_frame_info as forward_fill_missing_frame_info,
)

def _set_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Applies predefined datatypes to the input DataFrame fields.

    This service function is used to configure the input Pandas DataFrame, constructed from the data loaded from the
    GIMBL JSON log, to use the correct types for each column (field).

    Args:
        df: The Pandas DataFrame to convert.

    Returns:
        The updated Pandas DataFrame that now uses correct datatypes for each column.
    """

def _load_gimbl_log(log_file_path: Path) -> pd.DataFrame:
    """Loads data stored in the GIMBL log JSON file and returns it as a normalized Polar Dataframes with correct
    datatypes.

    Args:
        log_file_path: The path to the GIMBL log JSON file.

    Returns:
        The loaded data as a type-corrected Pandas DataFrame.
    """

def _parse_custom_msg(
    df: pd.DataFrame,
    message: str,
    fields: list[str],
    frames: pd.DataFrame = ...,
    rename_columns: dict[str, str] | None = None,
    msg_field: str = "msg",
    data_field: str = "data",
    remove_nan: bool = False,
) -> pd.DataFrame:
    """Parses target GIMBL messages from a DataFrame using specified fields.

    This service function serves as a wrapper for processing various GIMBl messages stored in the input DataFrame. It is
    iteratively applied to the DataFrame that stores raw data loaded from the GIMBL JSON log to convert it into a format
    compatible with all other processing functions in this package.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        message: The identifier (type) of the message to parse.
        fields: The list of field (column) names from which to extract the message data.
        frames: A Pandas DataFrame that stores the Mesoscope frame data, including timestamps. This allows optionally
            aligning parsed messages to Mesoscope frame acquisition times.
        rename_columns: A mapping of original column names to new names. This allows optionally renaming the extracted
            columns.
        msg_field: The name of the column in the input DataFrame where to search for the message identifier.
        data_field: The name of the column in the input DataFrame from which to extract the message data.
        remove_nan: Determines whether to remove NaN values from the extracted data.

    Returns:
        The Pandas DataFrame that stores the parsed data.
    """

def _parse_frames(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts Mesoscope frame timestamps from the input raw DataFrame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame indexed by Mesoscope frames and containing the 'time_us' column.
    """

def _parse_position(df: pd.DataFrame) -> pd.DataFrame:
    """Parses actor (animal) position and heading information from the input raw DataFrame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'x', 'y', 'z', and 'heading' columns.
    """

def _get_position_per_frame(position: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Merges the position and Mesoscope frame data to generate a per-frame position dataset.

    Args:
        position: The Pandas DataFrame that stores the actor (animal) position data.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'heading', 'x', 'y', 'z', and 'position' columns and each
        row represents a Mesoscope frame ordered sequentially.
    """

def _parse_path(df: pd.DataFrame) -> pd.DataFrame:
    """Parses the animal's position along the VR path from the input raw DataFrame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame with 'time_us', 'path', and 'position' columns.
    """

def _get_path_position_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Derives and returns a dataset that stores the animal's position along the VR path per each Mesoscope frame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'heading', 'path', and 'position' columns and each
        row represents a Mesoscope frame ordered sequentially.
    """

def _parse_camera(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses the camera frame information and aligns it to Mesoscope frames.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame indexed by camera frame and ID.
    """

def _parse_reward(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses the reward information and aligns it to the Mesoscope frames.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """

def _parse_idle_sound(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses the idle period sound information and aligns it to the Mesoscope frames.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """

def _parse_session_info(df: pd.DataFrame) -> dict[str, str | None]:
    """Parses session information from raw DataFrame rows labeled 'Info'.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The dictionary that contains the 'date_time', 'project', and 'scene' fields.
    """

def _parse_spherical_settings(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses spherical VR controller settings.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """

def _parse_spherical_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parses spherical VR controller data.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that contains the 'roll', 'yaw', and 'pitch' columns.
    """

def _parse_linear_settings(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """ParseS linear VR controller settings.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """

def _parse_linear_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parses linear VR controller data.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that stores the extracted linear movement information.
    """

def _get_linear_data_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Merges the linear movement datasets with the Mesoscope frame dataset.

    Args:
        df: The Pandas DataFrame that stores the parsed linear movement data.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us' and 'move' columns, aligned to the Mesoscope frames.
    """

def _get_spherical_data_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Merges the spherical movement datasets with the Mesoscope frame dataset.

    Args:
        df: The Pandas DataFrame that stores the parsed spherical movement data.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'roll', 'yaw', and 'pitch' columns, aligned to the Mesoscope
        frames.
    """

def parse_session_events(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts and standardizes the information about the session event markers.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame with columns 'time_us' and 'msg', where 'msg' is standardized and categorical. The 'msg'
        column includes the following values: StartTask (Indicates the start of a run/task period);
        EndTask (indicates the end of a run/task period); StartDark (indicates the start of a rest/dark period);
        EndDark (indicates the end of a rest/dark period); StartTeleportation (indicates the end of the previous trial);
        StartTrial (indicates the end of the previous teleportation).
    """

def parse_period_info(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts and standardizes the information about the task periods present in the parsed session data.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that stores available period data with the following columns: "time_start_us",
        "time_end_us", "period" (DARK or TASK), "set" (Wall cue set used during the period) and "is_guided" (Whether
        the period required licking for water reward dispersion).
    """

def parse_trial_info(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts the information about session's trials.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that stores the extracted trial information with columns: 'trial_number', 'time_start_us'
        'set' (The VR wall cue set used during trial), 'reward_id' (The reward region wall cue ID),
        'status' (The outcome of the trial, one of the following: CORRECT, INCORRECT, NO_RESPONSE, INCOMPLETE).
    """

def _process_gimbl_df(df: pd.DataFrame) -> tuple[pd.DataFrame, GimblData]:
    """Processes the input Pandas DataFrame that stores raw GIMBL log data into standardized parsed DataFrame and
    GimblData objects.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The processed data stored in a Pandas DataFrame and GimblData instance.
    """

def parse_gimbl_log(log_file_path: Path) -> tuple[pd.DataFrame, GimblData]:
    """Parses a GIMBL log file into a normalized Pandas DataFrame and a GimblData instance.

    Args:
        log_file_path: The path to the GIMBL log JSON file.

    Returns:
        The parsed data stored inside a normalized Pandas DataFrame and a GimblData instance.
    """
