"""This module provides the tools to read and parse the data stored inside the GIMBL JSON log files. It is used to
create an intermediate standardized data representation which is then stored as individual .feather files for further
processing."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .data import GimblData, FieldTypes
from .transform import (
    assign_frame_info,
    convert_lick_data,
    convert_reward_data,
    forward_fill_missing_frame_info,
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

    # Extracts the mapping of fields to their expected datatypes
    fields = FieldTypes().fields

    # Applies the datatypes to each column and, for numeric columns, converts Null values to 0.
    for key in fields.keys():
        if key in df:
            if fields[key] == "int":
                df[key] = df[key].fillna(0)
            df[key] = df[key].astype(fields[key])  # type: ignore
    return df


def _load_gimbl_log(log_file_path: Path) -> pd.DataFrame:
    """Loads data stored in the GIMBL log JSON file and returns it as a normalized Polar Dataframes with correct
    datatypes.

    Args:
        log_file_path: The path to the GIMBL log JSON file.

    Returns:
        The loaded data as a type-corrected Pandas DataFrame.
    """

    # Loads the data
    with open(log_file_path) as data_file:
        file_data = json.load(data_file)

    # Converts to DataFrame
    df = pd.json_normalize(file_data)

    # Applies datatypes
    df = _set_data_types(df)
    return df


def _parse_custom_msg(
    df: pd.DataFrame,
    message: str,
    fields: list[str],
    frames: pd.DataFrame = pd.DataFrame(),
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
    data = pd.DataFrame(columns=["index", "time_us", "frame"] + fields).set_index("index")
    if msg_field in df:
        idx = df[msg_field] == message
        # noinspection PyTypeChecker
        if any(idx):
            data_fields = ["time_us"] + [f"{data_field}.{field}" for field in fields]
            missing = [col for col in data_fields if col not in df.columns]
            if missing:
                raise NameError(f"Missing columns for parse_custom_msg: {missing}")
            data = df.loc[idx, data_fields].reset_index().set_index("index")
            # Renames any specified columns
            for field in fields:
                original_col = f"{data_field}.{field}"
                if rename_columns is not None and field in rename_columns:
                    data = data.rename(columns={original_col: rename_columns[field]})
                else:
                    data = data.rename(columns={original_col: field})

            # If frames exist, assigns Mesoscope frame indices to parsed messages
            if not frames.empty:
                data = assign_frame_info(data, frames, remove_nan=remove_nan)
            else:
                data["frame"] = None
                data = data.reset_index(drop=True)

        data = data.reset_index().set_index("index")
    return data


def _parse_frames(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts Mesoscope frame timestamps from the input raw DataFrame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame indexed by Mesoscope frames and containing the 'time_us' column.
    """
    frames = _parse_custom_msg(df, "microscope frame", [], msg_field="data.msg")

    # _parse_custom_msg() call above adds a 'frame' column, which is no longer used, so removes this extra column
    frames = frames.drop(columns="frame")
    frames = frames.rename_axis("frame")
    return frames


def _parse_position(df: pd.DataFrame) -> pd.DataFrame:
    """Parses actor (animal) position and heading information from the input raw DataFrame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'x', 'y', 'z', and 'heading' columns.
    """
    position = _parse_custom_msg(df, "Position", ["name", "position", "heading"])
    position = position.reset_index().set_index(["index", "name"]).drop(columns="frame")

    # Converts position to cm
    position["position"] = position["position"].apply(
        lambda x: np.asarray(x) / 100 if isinstance(x, list) else x  # type: ignore
    )
    position["x"] = position["position"].apply(lambda x: x[0] if isinstance(x, np.ndarray) else np.nan)
    position["y"] = position["position"].apply(lambda x: x[1] if isinstance(x, np.ndarray) else np.nan)
    position["z"] = position["position"].apply(lambda x: x[2] if isinstance(x, np.ndarray) else np.nan)

    # Converts Y axis rotation to heading in degrees. This is only used for spherical treadmill tasks, so likely not
    # important for Tyche data processing
    position["heading"] = position["heading"].apply(
        lambda x: np.asarray(x)[1] / 1000 if isinstance(x, list) else np.nan
    )
    return position


def _get_position_per_frame(position: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Merges the position and Mesoscope frame data to generate a per-frame position dataset.

    Args:
        position: The Pandas DataFrame that stores the actor (animal) position data.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'heading', 'x', 'y', 'z', and 'position' columns and each
        row represents a Mesoscope frame ordered sequentially.
    """

    # If either input dataframe is empty, instead returns an empty DataFrame initialized to store expected columns.
    if frames.empty or position.empty:
        return pd.DataFrame(columns=["time_us", "heading", "x", "y", "z", "position"])

    frame_position = assign_frame_info(position, frames)

    # Groups by frame, actor and averages the integer time_us (though time_us is typically consistent per group)
    frame_position = (
        frame_position.groupby(["frame", "name"], observed=True)
        .agg(
            {
                "time_us": "mean",
                "heading": "mean",
                "x": "mean",
                "y": "mean",
                "z": "mean",
            }
        )
        .reset_index()
        .set_index(["frame", "name"])
    )
    frame_position["time_us"] = frame_position["time_us"].astype("int64")
    frame_position["position"] = frame_position[["x", "y", "z"]].to_numpy().tolist()

    # Fills missing values
    frame_position = forward_fill_missing_frame_info(
        frame_position,
        frames,
        nan_fill=False,
        subset_columns=["heading", "x", "y", "z", "time_us"],
    )
    return frame_position[["time_us", "heading", "x", "y", "z", "position"]]


def _parse_path(df: pd.DataFrame) -> pd.DataFrame:
    """Parses the animal's position along the VR path from the input raw DataFrame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame with 'time_us', 'path', and 'position' columns.
    """
    path = _parse_custom_msg(df, "Path Position", ["name", "pathName", "position"], rename_columns={"pathName": "path"})
    path = path.reset_index().set_index(["index", "name"]).drop(columns="frame")
    path["position"] = path["position"].apply(lambda x: x / 100 if pd.notnull(x) else np.nan)
    return path


def _get_path_position_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Derives and returns a dataset that stores the animal's position along the VR path per each Mesoscope frame.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'heading', 'path', and 'position' columns and each
        row represents a Mesoscope frame ordered sequentially.
    """
    path = _parse_custom_msg(
        df,
        "Path Position",
        ["name", "pathName", "position"],
        rename_columns={"pathName": "path"},
        remove_nan=True,
        frames=frames,
    )
    if path.empty:
        return pd.DataFrame(columns=["time_us", "path", "position"])

    path["position"] = path["position"].apply(lambda x: x / 100 if pd.notnull(x) else np.nan)
    path = path.groupby(["frame", "name", "path"], observed=True).first()
    path = path.reset_index().drop_duplicates(subset=["frame", "name"], keep="first")
    path = path.reset_index().set_index(["frame", "name"]).drop(columns="index")
    path = forward_fill_missing_frame_info(path, frames, nan_fill=False, subset_columns=["time_us", "path", "position"])
    if not path.empty:
        path = path.bfill(axis=0)
    return path[["time_us", "path", "position"]]


def _parse_camera(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses the camera frame information and aligns it to Mesoscope frames.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame indexed by camera frame and ID.
    """
    camera = _parse_custom_msg(
        df, "Camera Frame", ["id"], frames=frames, msg_field="data.msg.event", data_field="data.msg"
    )
    camera = camera.rename_axis("cam_frame")
    if "id" in camera:
        camera["id"] = camera["id"].astype("int8")
    return camera.reset_index().set_index(["cam_frame", "id"])


def _parse_reward(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses the reward information and aligns it to the Mesoscope frames.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """
    msg = "Reward Delivery"
    fields = ["type", "amount", "valveTime", "withSound", "frequency", "duration"]
    rename = {
        "valveTime": "valve_time",
        "withSound": "sound_on",
        "frequency": "sound_freq",
        "duration": "sound_duration",
    }
    reward = _parse_custom_msg(
        df,
        msg,
        fields,
        rename_columns=rename,
        frames=frames,
        msg_field="data.msg.action",
        data_field="data.msg",
    )
    if "type" in reward:
        reward["type"] = reward["type"].astype("category")
    return reward


def _parse_idle_sound(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses the idle period sound information and aligns it to the Mesoscope frames.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """
    idle = _parse_custom_msg(
        df,
        "Idle Sound",
        ["type", "duration", "sound"],
        frames=frames,
        msg_field="data.msg.action",
        data_field="data.msg",
    )
    if not idle.empty:
        idle["type"] = idle["type"].astype("category")
        idle["sound"] = idle["sound"].astype("category")
    return idle


def _parse_session_info(df: pd.DataFrame) -> dict[str, str | None]:
    """Parses session information from raw DataFrame rows labeled 'Info'.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The dictionary that contains the 'date_time', 'project', and 'scene' fields.
    """
    info: pd.DataFrame | dict[str, str | None] = _parse_custom_msg(
        df, "Info", ["time", "project", "scene"], rename_columns={"time": "date_time"}
    ).drop(columns="frame", errors="ignore")
    if not isinstance(info, dict) and not info.empty:
        temporary_view = info.to_numpy().transpose()
        info = {
            "date_time": temporary_view[1].item(),
            "project": temporary_view[2].item(),
            "scene": temporary_view[3].item(),
        }
    else:
        info = {"date_time": None, "project": None, "scene": None}
    return info


def _parse_spherical_settings(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parses spherical VR controller settings.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """
    msg = "Spherical Controller Settings"
    fields = [
        "name",
        "isActive",
        "loopPath",
        "gain.forward",
        "gain.backward",
        "gain.strafeLeft",
        "gain.strafeRight",
        "gain.turnLeft",
        "gain.turnRight",
        "trajectory.maxRotPerSec",
        "trajectory.angleOffsetBias",
        "trajectory.minSpeed",
        "inputSmooth",
    ]
    rename = {
        "isActive": "is_active",
        "gain.forward": "gain_forward",
        "gain.backward": "gain_backward",
        "gain.strafeLeft": "gain_strafe_left",
        "gain.strafeRight": "gain_strafe_right",
        "gain.turnLeft": "gain_turn_left",
        "gain.turnRight": "gain_turn_right",
        "trajectory.maxRotPerSec": "trajectory_max_rot_per_sec",
        "trajectory.angleOffsetBias": "trajectory_angle_offset_bias",
        "trajectory.minSpeed": "trajectory_min_speed",
        "inputSmooth": "input_smooth",
        "loopPath": "is_looping",
    }
    settings = _parse_custom_msg(df, msg, fields, frames=frames, rename_columns=rename)
    settings["index"] = settings.groupby("name", observed=True).cumcount()
    return settings.set_index(["index", "name"])


def _parse_spherical_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parses spherical VR controller data.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that contains the 'roll', 'yaw', and 'pitch' columns.
    """
    data = _parse_custom_msg(df, "Spherical Controller", ["name", "roll", "yaw", "pitch"])
    data = data.reset_index().set_index(["index", "name"]).drop(columns="frame", errors="ignore")
    data["roll"] /= 100
    data["pitch"] /= 100
    data["yaw"] /= 1000
    return data


def _parse_linear_settings(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """ParseS linear VR controller settings.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that stores the extracted data.
    """
    msg = "Linear Controller Settings"
    fields = ["name", "isActive", "loopPath", "gain.forward", "gain.backward", "inputSmooth"]
    rename = {
        "isActive": "is_active",
        "loopPath": "is_looping",
        "gain.forward": "gain_forward",
        "gain.backward": "gain_backward",
        "inputSmooth": "input_smooth",
    }
    settings = _parse_custom_msg(df, msg, fields, frames=frames, rename_columns=rename)
    settings["index"] = settings.groupby("name", observed=True).cumcount()
    return settings.set_index(["index", "name"])


def _parse_linear_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parses linear VR controller data.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that stores the extracted linear movement information.
    """
    data = _parse_custom_msg(df, "Linear Controller", ["name", "move"])
    data = data.reset_index().set_index(["index", "name"]).drop(columns="frame", errors="ignore")
    data["move"] /= 100
    return data


def _get_linear_data_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Merges the linear movement datasets with the Mesoscope frame dataset.

    Args:
        df: The Pandas DataFrame that stores the parsed linear movement data.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us' and 'move' columns, aligned to the Mesoscope frames.
    """
    data = _parse_custom_msg(df, "Linear Controller", ["name", "move"], frames=frames, remove_nan=True)
    data = data.reset_index().set_index(["index", "name"])
    if data.empty:
        return data
    data["move"] /= 100
    # Sums movement within each frame
    grouped = data.groupby(["frame", "name"], observed=True).agg({"move": "sum", "time_us": "first"}).reset_index()
    grouped = grouped.set_index(["frame", "name"])
    # Forward fills missing
    grouped = forward_fill_missing_frame_info(grouped, frames, nan_fill=True, subset_columns=["move"])
    grouped = forward_fill_missing_frame_info(grouped, frames, nan_fill=False, subset_columns=["move"])
    return grouped[["time_us", "move"]]


def _get_spherical_data_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Merges the spherical movement datasets with the Mesoscope frame dataset.

    Args:
        df: The Pandas DataFrame that stores the parsed spherical movement data.
        frames: The Pandas DataFrame that stores Mesoscope frame timestamps.

    Returns:
        The Pandas DataFrame that contains the 'time_us', 'roll', 'yaw', and 'pitch' columns, aligned to the Mesoscope
        frames.
    """
    data = _parse_custom_msg(
        df, "Spherical Controller", ["name", "roll", "yaw", "pitch"], frames=frames, remove_nan=True
    )
    data = data.reset_index().set_index(["index", "name"])
    if data.empty:
        return data
    data["roll"] /= 100
    data["yaw"] /= 1000
    data["pitch"] /= 100
    grouped = (
        data.groupby(["frame", "name"], observed=True)
        .agg({"roll": "sum", "yaw": "sum", "pitch": "sum", "time_us": "first"})
        .reset_index()
        .set_index(["frame", "name"])
    )
    # Forward fills missing data
    grouped = forward_fill_missing_frame_info(grouped, frames, nan_fill=True, subset_columns=["roll", "yaw", "pitch"])
    grouped = forward_fill_missing_frame_info(grouped, frames, nan_fill=False, subset_columns=["roll", "yaw", "pitch"])
    return grouped[["time_us", "roll", "yaw", "pitch"]]


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
    # Filters relevant event rows
    session_events = df.loc[df.msg.isin(["StartPeriod", "StartTrial", "EndTrial", "EndPeriod"])].copy()

    # Defines conditions and corresponding new message labels
    conditions = [
        (session_events["data.type"] == "TASK") & (session_events["msg"] == "StartPeriod"),
        (session_events["data.type"] == "TASK") & (session_events["msg"] == "EndPeriod"),
        (session_events["data.type"] == "DARK") & (session_events["msg"] == "StartPeriod"),
        (session_events["data.type"] == "DARK") & (session_events["msg"] == "EndPeriod"),
        (session_events["msg"] == "EndTrial"),
    ]
    choices = ["StartTask", "EndTask", "StartDark", "EndDark", "StartTeleportation"]

    # Applies new labels
    session_events["msg"] = np.select(conditions, choices, default=session_events["msg"])

    # Converts 'msg' to categorical
    session_events["msg"] = session_events["msg"].astype("category")

    # Selects and return relevant columns
    session_events = session_events[["time_us", "msg"]].reset_index(drop=True)
    return session_events


def parse_period_info(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts and standardizes the information about the task periods present in the parsed session data.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that stores available period data with the following columns: "time_start_us",
        "time_end_us", "period" (DARK or TASK), "set" (Wall cue set used during the period) and "is_guided" (Whether
        the period required licking for water reward dispersion).
    """
    # Extract start period information
    start_periods = (
        df.loc[df["msg"] == "StartPeriod", ["time_us", "data.type", "data.cueSet", "data.isGuided"]]
        .reset_index(drop=True)
        .rename(
            columns={
                "time_us": "time_start_us",
                "data.type": "period",
                "data.cueSet": "set",
                "data.isGuided": "is_guided",
            }
        )
    )

    # Standardizes period type and set columns
    start_periods["period"] = (
        start_periods["period"].str.upper().astype("category").cat.set_categories(["DARK", "TASK"])
    )
    start_periods["set"] = start_periods["set"].astype("category")

    # Extracts end period information
    end_periods = (
        df.loc[df["msg"] == "EndPeriod", ["time_us"]].reset_index(drop=True).rename(columns={"time_us": "time_end_us"})
    )

    # Merges start and end periods
    period_info = pd.concat([start_periods, end_periods], axis=1)

    # Fills missing end times with the last timestamp in the dataframe
    period_info["time_end_us"] = period_info["time_end_us"].fillna(df["time_us"].iloc[-1])

    # Ensures time columns are of the integer type
    period_info["time_start_us"] = period_info["time_start_us"].astype(int)
    period_info["time_end_us"] = period_info["time_end_us"].astype(int)

    # Reorders columns for clarity
    period_info = period_info[["time_start_us", "time_end_us", "period", "set", "is_guided"]]

    return period_info


def parse_trial_info(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts the information about session's trials.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The Pandas DataFrame that stores the extracted trial information with columns: 'trial_number', 'time_start_us'
        'set' (The VR wall cue set used during trial), 'reward_id' (The reward region wall cue ID),
        'status' (The outcome of the trial, one of the following: CORRECT, INCORRECT, NO_RESPONSE, INCOMPLETE).
    """
    # Extracts trial start info
    trial_info = df.loc[
        df["msg"] == "StartTrial", ["time_us", "data.trialNum", "data.rewardSet", "data.rewardingCueId"]
    ]
    trial_info = trial_info.rename(
        columns={
            "data.trialNum": "trial_number",
            "data.rewardSet": "set",
            "data.rewardingCueId": "reward_id",
            "time_us": "time_start_us",
        }
    )
    trial_info = trial_info.astype({"trial_number": "int", "set": "category", "reward_id": "uint"})
    trial_info = trial_info.reset_index(drop=True)

    # Extracts trial end info
    end_info = df.loc[df["msg"] == "EndTrial", ["time_us", "data.trialNum", "data.status"]]
    end_info = end_info.rename(
        columns={"data.trialNum": "trial_number", "data.status": "status", "time_us": "time_end_us"}
    )
    end_info = end_info.reset_index(drop=True)
    end_info = end_info.loc[end_info["trial_number"] >= 0]

    # Merges start and end info
    trial_info = pd.merge(trial_info, end_info, on="trial_number", how="outer")

    # Handles incomplete trials
    trial_info["status"] = trial_info["status"].fillna("INCOMPLETE").astype("category")
    trial_info["status"] = trial_info["status"].replace("IN_PROGRESS", "INCOMPLETE")
    trial_info["status"] = trial_info["status"].cat.set_categories(
        ["CORRECT", "INCORRECT", "NO_RESPONSE", "INCOMPLETE"]
    )

    # Reorders columns and drop duplicates
    trial_info = trial_info[["trial_number", "time_start_us", "set", "reward_id", "status"]]
    trial_info = trial_info.drop_duplicates(subset="trial_number")

    return trial_info


def _process_gimbl_df(df: pd.DataFrame) -> tuple[pd.DataFrame, GimblData]:
    """Processes the input Pandas DataFrame that stores raw GIMBL log data into standardized parsed DataFrame and
    GimblData objects.

    Args:
        df: The Pandas DataFrame that stores the data loaded from the GIMBL JSON log file.

    Returns:
        The processed data stored in a Pandas DataFrame and GimblData instance.
    """
    # Pre-initializes the dataclass
    data = GimblData()

    # Populates GimblData object
    data.info = _parse_session_info(df)
    frames = _parse_frames(df)
    data.frames = frames
    data.position.time = _parse_position(df)
    data.position.frame = _get_position_per_frame(data.position.time, frames)
    data.path.time = _parse_path(df)
    data.path.frame = _get_path_position_per_frame(df, frames)
    data.camera = _parse_camera(df, frames)
    data.reward = _parse_reward(df, frames)
    data.reward = convert_reward_data(data.reward)
    data.lick = _parse_custom_msg(df, "Lick", [], frames=frames)
    data.lick = convert_lick_data(data.lick)
    data.idle.sound = _parse_idle_sound(df, frames)
    data.linear_controller.settings = _parse_linear_settings(df, frames)
    data.spherical_controller.settings = _parse_spherical_settings(df, frames)
    data.linear_controller.time = _parse_linear_data(df)
    data.spherical_controller.time = _parse_spherical_data(df)
    data.linear_controller.frame = _get_linear_data_per_frame(df, frames)
    data.spherical_controller.frame = _get_spherical_data_per_frame(df, frames)

    return df, data


def parse_gimbl_log(log_file_path: Path) -> tuple[pd.DataFrame, GimblData]:
    """Parses a GIMBL log file into a normalized Pandas DataFrame and a GimblData instance.

    Args:
        log_file_path: The path to the GIMBL log JSON file.

    Returns:
        The parsed data stored inside a normalized Pandas DataFrame and a GimblData instance.
    """
    # Loads the data from the .JSON file
    df = _load_gimbl_log(log_file_path)

    # Converts times to microseconds relative to the “Info” timestamp (in EST, converted to UTC).
    start_time_est = pd.Timestamp(df[df.msg == "Info"]["data.time"].to_numpy()[0], tz="EST")
    start_time_utc = start_time_est.tz_convert("UTC")
    df["time"] = pd.to_timedelta(df["time"], unit="ms")
    df["absolute_time"] = start_time_utc + df["time"]
    df["time_us"] = df["absolute_time"].astype("int64") // 1000
    df = df.drop(columns=["time", "absolute_time"])
    df = df[["time_us"] + [c for c in df.columns if c != "time_us"]]

    return _process_gimbl_df(df)
