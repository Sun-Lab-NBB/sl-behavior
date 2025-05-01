import json

import numpy as np
import pandas as pd

from .data import GimblData, FieldTypes
from .transform import assign_frame_info, ffill_missing_frame_info


def parse_gimbl_log(file_loc, verbose=False):
    data = GimblData()
    # load file.
    with open(file_loc) as data_file:
        file_data = json.load(data_file)
    df = pd.json_normalize(file_data)
    df = set_data_types(df)

    # Convert times to microseconds relative to the “Info” timestamp (in EST, converted to UTC).
    start_time_est = pd.Timestamp(df[df.msg == "Info"]["data.time"].to_numpy()[0], tz="EST")
    start_time_utc = start_time_est.tz_convert("UTC")
    # First, convert df["time"] (in ms) into a Timedelta, then shift by the UTC start_time:
    df["time"] = pd.to_timedelta(df["time"], unit="ms")
    df["absolute_time"] = start_time_utc + df["time"]
    df["time_us"] = df["absolute_time"].astype("int64") // 1000
    # Drop old columns
    df = df.drop(columns=["time", "absolute_time"])
    # Put time_us as the first column
    df = df[["time_us"] + [c for c in df.columns if c != "time_us"]]

    # get session info.
    data.info = parse_session_info(df)
    # get frame info.
    frames = parse_frames(df)
    data.frames = frames
    # get absolute position info
    data.position.time = parse_position(df)
    data.position.frame = get_position_per_frame(data.position.time, frames)
    #get path position.
    data.path.time = parse_path(df)
    data.path.frame = get_path_position_per_frame(df, frames)
    # camera info.
    data.camera = parse_camera(df, frames)
    # reward info.
    data.reward = parse_reward(df, frames)
    # lick info.
    data.lick = parse_custom_msg(df, "Lick", [], frames=frames)
    # idle info
    data.idle.sound = parse_idle_sound(df, frames)
    # controller info
    data.linear_controller.settings = parse_linear_settings(df, frames)
    data.spherical_controller_settings = parse_spherical_settings(df, frames)
    # controller data.
    data.linear_controller.time = parse_linear_data(df)
    data.spherical_controller.time = parse_spherical_data(df)
    data.linear_controller.frame = get_linear_data_per_frame(df, frames)
    data.spherical_controller.frame = get_spherical_data_per_frame(df, frames)
    return df, data


def set_data_types(df):
    """
    Applies the field types defined in FieldTypes().fields, except we no longer convert 'time' to Timedelta here.
    """
    fields = FieldTypes().fields
    for key in fields.keys():
        if key in df:
            if fields[key] == "int":
                df[key] = df[key].fillna(0)
            df[key] = df[key].astype(fields[key])
    return df


def parse_custom_msg(
    df, msg, fields, frames=pd.DataFrame(), rename_columns={}, msg_field="msg", data_field="data", remove_nan=False
):
    """
    Main parsing function. Looks for `msg` in df[msg_field] and pulls out requested fields plus time_us.
    Returns a DataFrame with columns [index, time_us, frame] + fields.
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
                if field in rename_columns:
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


def parse_frames(df):
    """Reads frame timestamps from gimbl log and returns a DataFrame with `time_us` for each frame."""
    frames = parse_custom_msg(df, "microscope frame", [], msg_field="data.msg")
    # parse_custom_msg adds a 'frame' col, which we don’t actually need here
    frames = frames.drop(columns="frame")
    frames = frames.rename_axis("frame")
    return frames


def parse_position(df):
    """Parses position information (actor name, position, heading) and returns a DataFrame with time_us, x, y, z, heading."""
    position = parse_custom_msg(df, "Position", ["name", "position", "heading"])
    position = position.reset_index().set_index(["index", "name"]).drop(columns="frame")
    # Convert position to cm
    position["position"] = position["position"].apply(lambda x: np.asarray(x) / 100 if isinstance(x, list) else x)
    position["x"] = position["position"].apply(lambda x: x[0] if isinstance(x, np.ndarray) else np.nan)
    position["y"] = position["position"].apply(lambda x: x[1] if isinstance(x, np.ndarray) else np.nan)
    position["z"] = position["position"].apply(lambda x: x[2] if isinstance(x, np.ndarray) else np.nan)
    # Convert Y axis rotation to heading in degrees
    position["heading"] = position["heading"].apply(lambda x: np.asarray(x)[1] / 1000 if isinstance(x, list) else np.nan)
    return position


def get_position_per_frame(position, frames):
    """Aggregates position data per frame, per actor. Uses time_us as an integer."""
    if frames.empty or position.empty:
        return pd.DataFrame(columns=["time_us", "heading", "x", "y", "z", "position"])
    frame_position = assign_frame_info(position, frames)
    # Group by frame, actor
    # We’ll average the integer time_us (though time_us is typically consistent per group)
    frame_position = (
        frame_position.groupby(["frame", "name"], observed=True)
        .agg({
            "time_us": "mean",
            "heading": "mean",
            "x": "mean",
            "y": "mean",
            "z": "mean",
        })
        .reset_index()
        .set_index(["frame", "name"])
    )
    frame_position["time_us"] = frame_position["time_us"].astype("int64")
    frame_position["position"] = frame_position[["x", "y", "z"]].to_numpy().tolist()

    # Fill missing
    frame_position = ffill_missing_frame_info(frame_position, frames, nan_fill=False, subset_columns=["heading", "x", "y", "z", "time_us"])
    return frame_position[["time_us", "heading", "x", "y", "z", "position"]]


def parse_path(df):
    """
    Parses path position info (actor name, pathName, position) and returns a DataFrame with time_us, path, position.
    """
    path = parse_custom_msg(df, "Path Position", ["name", "pathName", "position"], rename_columns={"pathName": "path"})
    path = path.reset_index().set_index(["index", "name"]).drop(columns="frame")
    path["position"] = path["position"].apply(lambda x: x / 100 if pd.notnull(x) else np.nan)
    return path


def get_path_position_per_frame(df, frames):
    """
    Gets path position per frame from the main DataFrame. Fills missing by bfill or ffill as needed.
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


def parse_camera(df, frames):
    """
    Parses camera frame info and aligns it to microscope frames (time_us).
    """
    camera = parse_custom_msg(df, "Camera Frame", ["id"], frames=frames, msg_field="data.msg.event", data_field="data.msg")
    camera = camera.rename_axis("cam_frame")
    if "id" in camera:
        camera["id"] = camera["id"].astype("int8")
    return camera.reset_index().set_index(["cam_frame", "id"])


def parse_reward(df, frames):
    """
    Parses reward info from gimbl log. Returns DataFrame with columns:
    time_us, frame, type, amount, valve_time, sound_on, sound_freq, sound_duration
    """
    msg = "Reward Delivery"
    fields = ["type", "amount", "valveTime", "withSound", "frequency", "duration"]
    rename = {
        "valveTime": "valve_time",
        "withSound": "sound_on",
        "frequency": "sound_freq",
        "duration": "sound_duration"
    }
    reward = parse_custom_msg(df, msg, fields, rename_columns=rename, frames=frames, msg_field="data.msg.action", data_field="data.msg")
    if "type" in reward:
        reward["type"] = reward["type"].astype("category")
    return reward


def parse_idle_sound(df, frames):
    """
    Parses idle sound info from gimbl log. Returns time_us, frame, type, duration, sound.
    """
    idle = parse_custom_msg(df, "Idle Sound", ["type", "duration", "sound"], frames=frames,
                            msg_field="data.msg.action", data_field="data.msg")
    if not idle.empty:
        idle["type"] = idle["type"].astype("category")
        idle["sound"] = idle["sound"].astype("category")
    return idle


def parse_session_info(df):
    """
    Reads session info from lines labeled 'Info'. Returns a dict with date_time, project, scene.
    """
    info = parse_custom_msg(df, "Info", ["time", "project", "scene"], rename_columns={"time": "date_time"}).drop(columns="frame", errors="ignore")
    if not info.empty:
        info = info.to_numpy().transpose()
        info = {
            "date_time": info[1].item(),
            "project": info[2].item(),
            "scene": info[3].item()
        }
    else:
        info = {"date_time": None, "project": None, "scene": None}
    return info


def parse_spherical_settings(df, frames):
    """
    Parses spherical controller settings, returning a DataFrame with time_us + various controller fields.
    """
    msg = "Spherical Controller Settings"
    fields = [
        "name", "isActive", "loopPath",
        "gain.forward", "gain.backward",
        "gain.strafeLeft", "gain.strafeRight",
        "gain.turnLeft", "gain.turnRight",
        "trajectory.maxRotPerSec", "trajectory.angleOffsetBias",
        "trajectory.minSpeed", "inputSmooth"
    ]
    rename = {
        "isActive": "is_active",
        "gain.forward": "gain_forward", "gain.backward": "gain_backward",
        "gain.strafeLeft": "gain_strafe_left", "gain.strafeRight": "gain_strafe_right",
        "gain.turnLeft": "gain_turn_left", "gain.turnRight": "gain_turn_right",
        "trajectory.maxRotPerSec": "trajectory_max_rot_per_sec",
        "trajectory.angleOffsetBias": "trajectory_angle_offset_bias",
        "trajectory.minSpeed": "trajectory_min_speed",
        "inputSmooth": "input_smooth",
        "loopPath": "is_looping"
    }
    settings = parse_custom_msg(df, msg, fields, frames=frames, rename_columns=rename)
    settings["index"] = settings.groupby("name", observed=True).cumcount()
    return settings.set_index(["index", "name"])


def parse_spherical_data(df):
    """
    Parses raw data for spherical controllers, returning time_us, roll (cm), yaw (deg), pitch (cm).
    """
    data = parse_custom_msg(df, "Spherical Controller", ["name", "roll", "yaw", "pitch"])
    data = data.reset_index().set_index(["index", "name"]).drop(columns="frame", errors="ignore")
    data["roll"] = data["roll"] / 100
    data["pitch"] = data["pitch"] / 100
    data["yaw"] = data["yaw"] / 1000
    return data


def parse_linear_settings(df, frames):
    """
    Parses linear controller settings, returning time_us + config fields.
    """
    msg = "Linear Controller Settings"
    fields = ["name", "isActive", "loopPath", "gain.forward", "gain.backward", "inputSmooth"]
    rename = {
        "isActive": "is_active",
        "loopPath": "is_looping",
        "gain.forward": "gain_forward",
        "gain.backward": "gain_backward",
        "inputSmooth": "input_smooth"
    }
    settings = parse_custom_msg(df, msg, fields, frames=frames, rename_columns=rename)
    settings["index"] = settings.groupby("name", observed=True).cumcount()
    return settings.set_index(["index", "name"])


def parse_linear_data(df):
    """
    Parses raw data from linear controllers, returning time_us + move in cm.
    """
    data = parse_custom_msg(df, "Linear Controller", ["name", "move"])
    data = data.reset_index().set_index(["index", "name"]).drop(columns="frame", errors="ignore")
    data["move"] = data["move"] / 100
    return data


def get_linear_data_per_frame(df, frames):
    """
    Sums linear movement data for each microscope frame. Returns columns time_us, move.
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


def get_spherical_data_per_frame(df, frames):
    """
    Sums spherical movement data within each frame. Returns columns time_us, roll, yaw, pitch.
    """
    data = parse_custom_msg(df, "Spherical Controller", ["name", "roll", "yaw", "pitch"], frames=frames, remove_nan=True)
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
