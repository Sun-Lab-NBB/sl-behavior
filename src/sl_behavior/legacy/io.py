import os

import pandas as pd


def export_gimbl_data(data, out_dir: str = "."):
    """Exports each table from 'data' (returned by parse_gimbl_log) to individual Feather files.

    Args:
        data (GimblData): Parsed GimblData object containing various DataFrames.
        out_dir (str): Destination folder for Feather files.
    """
    os.makedirs(out_dir, exist_ok=True)

    if hasattr(data, "frames") and isinstance(data.frames, pd.DataFrame):
        data.frames.to_feather(os.path.join(out_dir, "frames.feather"))

    if hasattr(data, "position"):
        if hasattr(data.position, "time") and isinstance(data.position.time, pd.DataFrame):
            data.position.time.to_feather(os.path.join(out_dir, "position_time.feather"))
        if hasattr(data.position, "frame") and isinstance(data.position.frame, pd.DataFrame):
            data.position.frame.to_feather(os.path.join(out_dir, "position_frame.feather"))

    if hasattr(data, "path"):
        if hasattr(data.path, "time") and isinstance(data.path.time, pd.DataFrame):
            data.path.time.to_feather(os.path.join(out_dir, "path_time.feather"))
        if hasattr(data.path, "frame") and isinstance(data.path.frame, pd.DataFrame):
            data.path.frame.to_feather(os.path.join(out_dir, "path_frame.feather"))

    if hasattr(data, "camera") and isinstance(data.camera, pd.DataFrame):
        data.camera.to_feather(os.path.join(out_dir, "camera.feather"))

    if hasattr(data, "reward") and isinstance(data.reward, pd.DataFrame):
        data.reward.to_feather(os.path.join(out_dir, "reward.feather"))

    if hasattr(data, "lick") and isinstance(data.lick, pd.DataFrame):
        data.lick.to_feather(os.path.join(out_dir, "lick.feather"))

    if hasattr(data, "idle") and hasattr(data.idle, "sound") and isinstance(data.idle.sound, pd.DataFrame):
        data.idle.sound.to_feather(os.path.join(out_dir, "idle_sound.feather"))

    if hasattr(data, "linear_controller"):
        if hasattr(data.linear_controller, "settings") and isinstance(data.linear_controller.settings, pd.DataFrame):
            data.linear_controller.settings.to_feather(os.path.join(out_dir, "linear_controller_settings.feather"))
        if hasattr(data.linear_controller, "time") and isinstance(data.linear_controller.time, pd.DataFrame):
            data.linear_controller.time.to_feather(os.path.join(out_dir, "linear_controller_time.feather"))
        if hasattr(data.linear_controller, "frame") and isinstance(data.linear_controller.frame, pd.DataFrame):
            data.linear_controller.frame.to_feather(os.path.join(out_dir, "linear_controller_frame.feather"))

    if hasattr(data, "spherical_controller"):
        if hasattr(data, "spherical_controller_settings") and isinstance(data.spherical_controller_settings, pd.DataFrame):
            data.spherical_controller_settings.to_feather(os.path.join(out_dir, "spherical_controller_settings.feather"))
        if hasattr(data.spherical_controller, "time") and isinstance(data.spherical_controller.time, pd.DataFrame):
            data.spherical_controller.time.to_feather(os.path.join(out_dir, "spherical_controller_time.feather"))
        if hasattr(data.spherical_controller, "frame") and isinstance(data.spherical_controller.frame, pd.DataFrame):
            data.spherical_controller.frame.to_feather(os.path.join(out_dir, "spherical_controller_frame.feather"))
