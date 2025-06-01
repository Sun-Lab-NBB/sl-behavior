import json
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

from .data import GimblData, FieldTypes
from .transform import (
    assign_frame_info,
    convert_lick_data,
    convert_reward_data,
    ffill_missing_frame_info,
)


def load_gimbl_log(file_loc: str) -> pd.DataFrame:
    """Loads a GIMBL log JSON file and returns a normalized DataFrame with correct data types.

    Args:
        file_loc (str): The file path to the GIMBL log JSON file.

    Returns:
        pd.DataFrame: The loaded and type-corrected DataFrame.
    """
    with open(file_loc) as data_file:
        file_data = json.load(data_file)
    df = pd.json_normalize(file_data)
    df = set_data_types(df)
    return df


def process_gimbl_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, GimblData]:
    """Processes a GIMBL DataFrame into a standardized DataFrame and GimblData object.

    Args:
        df (pd.DataFrame): The loaded GIMBL DataFrame.

    Returns:
        Tuple[pd.DataFrame, GimblData]: The processed DataFrame and GimblData object.
    """
    data = GimblData()

    # Populate GimblData object
    data.info = parse_session_info(df)
    frames = parse_frames(df)
    data.frames = frames
    data.position.time = parse_position(df)
    data.position.frame = get_position_per_frame(data.position.time, frames)
    data.path.time = parse_path(df)
    data.path.frame = get_path_position_per_frame(df, frames)
    data.camera = parse_camera(df, frames)
    data.reward = parse_reward(df, frames)
    data.reward = convert_reward_data(data.reward)
    data.lick = parse_custom_msg(df, "Lick", [], frames=frames)
    data.lick = convert_lick_data(data.lick)
    data.idle.sound = parse_idle_sound(df, frames)
    data.linear_controller.settings = parse_linear_settings(df, frames)
    data.spherical_controller_settings = parse_spherical_settings(df, frames)
    data.linear_controller.time = parse_linear_data(df)
    data.spherical_controller.time = parse_spherical_data(df)
    data.linear_controller.frame = get_linear_data_per_frame(df, frames)
    data.spherical_controller.frame = get_spherical_data_per_frame(df, frames)

    return df, data


def parse_gimbl_log(file_loc: str, verbose: bool = False) -> Tuple[pd.DataFrame, GimblData]:
    """Parse a GIMBL log file into a DataFrame and GimblData object.

    Args:
        file_loc (str): The file path to the GIMBL log JSON file.
        verbose (bool, optional): Whether to print debug information.

    Returns:
        Tuple[pd.DataFrame, GimblData]: The parsed DataFrame and GimblData object.

    Example:
        >>> df, data = parse_gimbl_log("path/to/log.json")
        >>> print(df.head())
        >>> print(data.info)
    """
    df = load_gimbl_log(file_loc)

    # Convert times to microseconds relative to the “Info” timestamp (in EST, converted to UTC).
    start_time_est = pd.Timestamp(df[df.msg == "Info"]["data.time"].to_numpy()[0], tz="EST")
    start_time_utc = start_time_est.tz_convert("UTC")
    df["time"] = pd.to_timedelta(df["time"], unit="ms")
    df["absolute_time"] = start_time_utc + df["time"]
    df["time_us"] = df["absolute_time"].astype("int64") // 1000
    df = df.drop(columns=["time", "absolute_time"])
    df = df[["time_us"] + [c for c in df.columns if c != "time_us"]]

    return process_gimbl_df(df, verbose=verbose)


def set_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """Apply predefined field types to a DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to convert.

    Returns:
        pd.DataFrame: The updated DataFrame with new types.
    """
    fields = FieldTypes().fields
    for key in fields.keys():
        if key in df:
            if fields[key] == "int":
                df[key] = df[key].fillna(0)
            df[key] = df[key].astype(fields[key])
    return df


def parse_custom_msg(
    df: pd.DataFrame,
    msg: str,
    fields: List[str],
    frames: pd.DataFrame = pd.DataFrame(),
    rename_columns: Dict[str, str] = None,
    msg_field: str = "msg",
    data_field: str = "data",
    remove_nan: bool = False,
) -> pd.DataFrame:
    """Parse custom messages from a DataFrame using specified fields.

    Args:
        df (pd.DataFrame): The main DataFrame.
        msg (str): The message identifier to parse.
        fields (List[str]): The list of field names to extract.
        frames (pd.DataFrame, optional): Frame data for alignment.
        rename_columns (Dict[str, str], optional): Column rename mappings.
        msg_field (str, optional): Name of the message column.
        data_field (str, optional): Name of the data column.
        remove_nan (bool, optional): Whether to remove NaN values.

    Returns:
        pd.DataFrame: A DataFrame with the relevant parsed fields.
    """
    data = pd.DataFrame(columns=["index", "time_us", "frame"] + fields).set_index("index")
    if msg_field in df:
        idx = df[msg_field] == msg
        if any(idx):
            data_fields = ["time_us"] + [f"{data_field}.{field}" for field in fields]
            missing = [col for col in data_fields if col not in df.columns]
            if missing:
                raise NameError(f"Missing columns for parse_custom_msg: {missing}")
            data = df.loc[idx, data_fields].reset_index().set_index("index")
            # Rename any specified columns
            for field in fields:
                original_col = f"{data_field}.{field}"
                if rename_columns is not None and field in rename_columns:
                    data = data.rename(columns={original_col: rename_columns[field]})
                else:
                    data = data.rename(columns={original_col: field})

            # If frames exist, assign microscope frame info
            if not frames.empty:
                data = assign_frame_info(data, frames, remove_nan=remove_nan)
            else:
                data["frame"] = None
                data = data.reset_index(drop=True)

        data = data.reset_index().set_index("index")
    return data


def parse_frames(df: pd.DataFrame) -> pd.DataFrame:
    """Extract microscope frame timestamps.

    Args:
        df (pd.DataFrame): The main DataFrame.

    Returns:
        pd.DataFrame: A DataFrame indexed by frame containing time_us.
    """
    frames = parse_custom_msg(df, "microscope frame", [], msg_field="data.msg")
    # parse_custom_msg adds a 'frame' col, which we don’t actually need here
    frames = frames.drop(columns="frame")
    frames = frames.rename_axis("frame")
    return frames


def parse_position(df: pd.DataFrame) -> pd.DataFrame:
    """Parse actor position and heading information.

    Args:
        df (pd.DataFrame): The DataFrame containing position entries.

    Returns:
        pd.DataFrame: A DataFrame with time_us, x, y, z, heading columns.
    """
    position = parse_custom_msg(df, "Position", ["name", "position", "heading"])
    position = position.reset_index().set_index(["index", "name"]).drop(columns="frame")
    # Convert position to cm
    position["position"] = position["position"].apply(lambda x: np.asarray(x) / 100 if isinstance(x, list) else x)
    position["x"] = position["position"].apply(lambda x: x[0] if isinstance(x, np.ndarray) else np.nan)
    position["y"] = position["position"].apply(lambda x: x[1] if isinstance(x, np.ndarray) else np.nan)
    position["z"] = position["position"].apply(lambda x: x[2] if isinstance(x, np.ndarray) else np.nan)
    # Convert Y axis rotation to heading in degrees
    position["heading"] = position["heading"].apply(
        lambda x: np.asarray(x)[1] / 1000 if isinstance(x, list) else np.nan
    )
    return position


def get_position_per_frame(position: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Aggregate position data per frame and actor.

    Args:
        position (pd.DataFrame): Actor position data.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: The DataFrame with time_us, heading, x, y, z, position columns.
    """
    if frames.empty or position.empty:
        return pd.DataFrame(columns=["time_us", "heading", "x", "y", "z", "position"])
    frame_position = assign_frame_info(position, frames)
    # Group by frame, actor
    # We’ll average the integer time_us (though time_us is typically consistent per group)
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

    # Fill missing
    frame_position = ffill_missing_frame_info(
        frame_position,
        frames,
        nan_fill=False,
        subset_columns=["heading", "x", "y", "z", "time_us"],
    )
    return frame_position[["time_us", "heading", "x", "y", "z", "position"]]


def parse_path(df: pd.DataFrame) -> pd.DataFrame:
    """Parse path position data.

    Args:
        df (pd.DataFrame): The DataFrame containing path data.

    Returns:
        pd.DataFrame: The DataFrame with time_us, path, and position columns.
    """
    path = parse_custom_msg(df, "Path Position", ["name", "pathName", "position"], rename_columns={"pathName": "path"})
    path = path.reset_index().set_index(["index", "name"]).drop(columns="frame")
    path["position"] = path["position"].apply(lambda x: x / 100 if pd.notnull(x) else np.nan)
    return path


def get_path_position_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Derive path positions for each frame.

    Args:
        df (pd.DataFrame): The main DataFrame with path info.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: A DataFrame with time_us, path, position columns.
    """
    path = parse_custom_msg(
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
    path = ffill_missing_frame_info(path, frames, nan_fill=False, subset_columns=["time_us", "path", "position"])
    if not path.empty:
        path = path.bfill(axis=0)
    return path[["time_us", "path", "position"]]


def parse_camera(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parse camera frame info and align it with microscope frames.

    Args:
        df (pd.DataFrame): The main DataFrame.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: The DataFrame indexed by camera frame and ID.
    """
    camera = parse_custom_msg(
        df, "Camera Frame", ["id"], frames=frames, msg_field="data.msg.event", data_field="data.msg"
    )
    camera = camera.rename_axis("cam_frame")
    if "id" in camera:
        camera["id"] = camera["id"].astype("int8")
    return camera.reset_index().set_index(["cam_frame", "id"])


def parse_reward(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parse reward info from the log.

    Args:
        df (pd.DataFrame): The main DataFrame.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: The DataFrame containing reward data.
    """
    msg = "Reward Delivery"
    fields = ["type", "amount", "valveTime", "withSound", "frequency", "duration"]
    rename = {
        "valveTime": "valve_time",
        "withSound": "sound_on",
        "frequency": "sound_freq",
        "duration": "sound_duration",
    }
    reward = parse_custom_msg(
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


def parse_idle_sound(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parse idle sound info from the log.

    Args:
        df (pd.DataFrame): The main DataFrame.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: The DataFrame with idle sound data.
    """
    idle = parse_custom_msg(
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


def parse_session_info(df: pd.DataFrame) -> Dict[str, Optional[str]]:
    """Read session info from lines labeled 'Info'.

    Args:
        df (pd.DataFrame): The main DataFrame.

    Returns:
        Dict[str, Optional[str]]: Dictionary containing date_time, project, and scene.
    """
    info = parse_custom_msg(df, "Info", ["time", "project", "scene"], rename_columns={"time": "date_time"}).drop(
        columns="frame", errors="ignore"
    )
    if not info.empty:
        info = info.to_numpy().transpose()
        info = {"date_time": info[1].item(), "project": info[2].item(), "scene": info[3].item()}
    else:
        info = {"date_time": None, "project": None, "scene": None}
    return info


def parse_spherical_settings(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parse spherical controller settings.

    Args:
        df (pd.DataFrame): The main DataFrame.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: A DataFrame containing spherical settings.
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
    settings = parse_custom_msg(df, msg, fields, frames=frames, rename_columns=rename)
    settings["index"] = settings.groupby("name", observed=True).cumcount()
    return settings.set_index(["index", "name"])


def parse_spherical_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parse spherical controller data.

    Args:
        df (pd.DataFrame): The main DataFrame.

    Returns:
        pd.DataFrame: The DataFrame with roll, yaw, pitch columns.
    """
    data = parse_custom_msg(df, "Spherical Controller", ["name", "roll", "yaw", "pitch"])
    data = data.reset_index().set_index(["index", "name"]).drop(columns="frame", errors="ignore")
    data["roll"] = data["roll"] / 100
    data["pitch"] = data["pitch"] / 100
    data["yaw"] = data["yaw"] / 1000
    return data


def parse_linear_settings(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Parse linear controller settings.

    Args:
        df (pd.DataFrame): The main DataFrame.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: A DataFrame containing linear settings.
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
    settings = parse_custom_msg(df, msg, fields, frames=frames, rename_columns=rename)
    settings["index"] = settings.groupby("name", observed=True).cumcount()
    return settings.set_index(["index", "name"])


def parse_linear_data(df: pd.DataFrame) -> pd.DataFrame:
    """Parse linear controller data.

    Args:
        df (pd.DataFrame): The main DataFrame.

    Returns:
        pd.DataFrame: The DataFrame with movement information.
    """
    data = parse_custom_msg(df, "Linear Controller", ["name", "move"])
    data = data.reset_index().set_index(["index", "name"]).drop(columns="frame", errors="ignore")
    data["move"] = data["move"] / 100
    return data


def get_linear_data_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Sum linear movement data within each frame.

    Args:
        df (pd.DataFrame): The DataFrame with linear controller data.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: The DataFrame with time_us, move columns.
    """
    data = parse_custom_msg(df, "Linear Controller", ["name", "move"], frames=frames, remove_nan=True)
    data = data.reset_index().set_index(["index", "name"])
    if data.empty:
        return data
    data["move"] = data["move"] / 100
    # Sum movement within each frame
    grouped = data.groupby(["frame", "name"], observed=True).agg({"move": "sum", "time_us": "first"}).reset_index()
    grouped = grouped.set_index(["frame", "name"])
    # Forward fill missing
    grouped = ffill_missing_frame_info(grouped, frames, nan_fill=True, subset_columns=["move"])
    grouped = ffill_missing_frame_info(grouped, frames, nan_fill=False, subset_columns=["move"])
    return grouped[["time_us", "move"]]


def get_spherical_data_per_frame(df: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
    """Sum spherical movement data within each frame.

    Args:
        df (pd.DataFrame): The DataFrame with spherical controller data.
        frames (pd.DataFrame): Frame timestamps.

    Returns:
        pd.DataFrame: The DataFrame with time_us, roll, yaw, pitch columns.
    """
    data = parse_custom_msg(
        df, "Spherical Controller", ["name", "roll", "yaw", "pitch"], frames=frames, remove_nan=True
    )
    data = data.reset_index().set_index(["index", "name"])
    if data.empty:
        return data
    data["roll"] = data["roll"] / 100
    data["yaw"] = data["yaw"] / 1000
    data["pitch"] = data["pitch"] / 100
    grouped = (
        data.groupby(["frame", "name"], observed=True)
        .agg({"roll": "sum", "yaw": "sum", "pitch": "sum", "time_us": "first"})
        .reset_index()
        .set_index(["frame", "name"])
    )
    # Forward fill missing
    grouped = ffill_missing_frame_info(grouped, frames, nan_fill=True, subset_columns=["roll", "yaw", "pitch"])
    grouped = ffill_missing_frame_info(grouped, frames, nan_fill=False, subset_columns=["roll", "yaw", "pitch"])
    return grouped[["time_us", "roll", "yaw", "pitch"]]


def parse_session_events(logs_df):  # -> Any:
    """Extracts and standardizes session event markers from the logs DataFrame.

    Args:
        logs_df (pd.DataFrame): The log DataFrame containing event messages.

    Returns:
        pd.DataFrame: DataFrame with columns ['time_us', 'msg'], where 'msg' is standardized and categorical.
        msg values include:
            - StartTask: Indicates the start of a run/task period.
            - EndTask: Indicates the end of a run/task period.
            - StartDark: Indicates the start of a rest/dark period.
            - EndDark: Indicates the end of a rest/dark period.
            - StartTeleportation: Also indicates the end of the previous trial.
            - StartTrial: Also indicates the end of the previous teleportation.
    """
    # Filter relevant event rows
    session_events = logs_df.loc[logs_df.msg.isin(["StartPeriod", "StartTrial", "EndTrial", "EndPeriod"])].copy()

    # Define conditions and corresponding new message labels
    conditions = [
        (session_events["data.type"] == "TASK") & (session_events["msg"] == "StartPeriod"),
        (session_events["data.type"] == "TASK") & (session_events["msg"] == "EndPeriod"),
        (session_events["data.type"] == "DARK") & (session_events["msg"] == "StartPeriod"),
        (session_events["data.type"] == "DARK") & (session_events["msg"] == "EndPeriod"),
        (session_events["msg"] == "EndTrial"),
    ]
    choices = ["StartTask", "EndTask", "StartDark", "EndDark", "StartTeleportation"]

    # Apply new labels
    session_events["msg"] = np.select(conditions, choices, default=session_events["msg"])

    # Convert 'msg' to categorical
    session_events["msg"] = session_events["msg"].astype("category")

    # Select and return relevant columns
    session_events = session_events[["time_us", "msg"]].reset_index(drop=True)
    return session_events


def parse_period_info(df):
    """Parses information on the periods present in the session (DARK/TASK).

    Args:
        df (pd.DataFrame): Raw dataframe generated by vr2p.gimbl.parse.parse_gimbl_log.

    Returns:
        pd.DataFrame: Period information with the following columns:
            - "time_start_us" (int): Start time of the period in microseconds.
            - "time_end_us" (int): End time of the period in microseconds.
            - "period" (category): Period type (DARK/TASK).
            - "set" (category): Cue set associated with the period.
            - "is_guided" (bool): Whether the period is guided.
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

    # Standardize period type and set columns
    start_periods["period"] = (
        start_periods["period"].str.upper().astype("category").cat.set_categories(["DARK", "TASK"])
    )
    start_periods["set"] = start_periods["set"].astype("category")

    # Extract end period information
    end_periods = (
        df.loc[df["msg"] == "EndPeriod", ["time_us"]].reset_index(drop=True).rename(columns={"time_us": "time_end_us"})
    )

    # Merge start and end periods
    period_info = pd.concat([start_periods, end_periods], axis=1)

    # Fill missing end times with the last timestamp in the dataframe
    period_info["time_end_us"] = period_info["time_end_us"].fillna(df["time_us"].iloc[-1])

    # Ensure time columns are of integer type
    period_info["time_start_us"] = period_info["time_start_us"].astype(int)
    period_info["time_end_us"] = period_info["time_end_us"].astype(int)

    # Reorder columns for clarity
    period_info = period_info[["time_start_us", "time_end_us", "period", "set", "is_guided"]]

    return period_info


def parse_trial_info(df):
    """Generates a trial info DataFrame from gimbl log.

    Args:
        df (pd.DataFrame): Raw dataframe generated by vr2p.gimbl.parse.parse_gimbl_log.

    Returns:
        pd.DataFrame: Trial info with columns:
            - "trial_number" (int): Trial number.
            - "time_start_us" (int): Start time of trial in microseconds.
            - "set" (category): Used cue set.
            - "reward_id" (int): ID of cue that was rewarding (starts at 1).
            - "status" (category): Result of trial (CORRECT, INCORRECT, NO_RESPONSE, INCOMPLETE).
    """
    # Extract trial start info
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

    # Extract trial end info
    end_info = df.loc[df["msg"] == "EndTrial", ["time_us", "data.trialNum", "data.status"]]
    end_info = end_info.rename(
        columns={"data.trialNum": "trial_number", "data.status": "status", "time_us": "time_end_us"}
    )
    end_info = end_info.reset_index(drop=True)
    end_info = end_info.loc[end_info["trial_number"] >= 0]

    # Merge start and end info
    trial_info = pd.merge(trial_info, end_info, on="trial_number", how="outer")

    # Handle incomplete trials
    trial_info["status"] = trial_info["status"].fillna("INCOMPLETE").astype("category")
    trial_info["status"] = trial_info["status"].replace("IN_PROGRESS", "INCOMPLETE")
    trial_info["status"] = trial_info["status"].cat.set_categories(
        ["CORRECT", "INCORRECT", "NO_RESPONSE", "INCOMPLETE"]
    )

    # Reorder columns and drop duplicates
    trial_info = trial_info[["trial_number", "time_start_us", "set", "reward_id", "status"]]
    trial_info = trial_info.drop_duplicates(subset="trial_number")

    return trial_info
