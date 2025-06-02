"""This module provides utility functions used to calculate movement speed and other metrics from position data stored
in DataFrames extracted from Gimbl logs.
"""

from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from ataraxis_base_utilities import console


def movement_speed(df: pd.DataFrame, window_size: int = 100, ignore_threshold: float = 20) -> NDArray[Any]:
    """Calculates the rolling average movement speed in centimeters per second (cm/s) from the input DataFrame.

    The DataFrame must contain either columns named "x", "y", "z", "time", or columns named "position", "path", "time".

    If "x", "y", and "z" are present, the function automatically calculates the distance in 3D space for each frame and
    assigns them to a temporary path "test". Otherwise, if "path" is present, it processes each path independently.

    Teleport artifacts or extremely large movements beyond the specified threshold are set to zero before rolling
    computation. The rolling window is indexed by the time column, which must be a Pandas Datetime column.

    Args:
        df: A Pandas DataFrame containing the required columns ("x", "y", "z", "time", or "position", "path", "time").
        window_size: The size of the rolling average window in milliseconds.
        ignore_threshold: The instantaneous traveled distance threshold, above which the movement is assumed to be a
            teleport artifact and set to zero.

    Returns:
        The 1-dimensional NumPy array of speed values (in cm/s) aligned with rows of the input DataFrame.

    Raises:
        KeyError: If the required columns ("time" and either "path" or "x", "y", "z") are missing from the DataFrame.

    Notes:
        The speed calculation is performed by computing the distance traveled between consecutive frames, then taking
        the rolling mean of these distances over the specified time window.
    """
    # Copies the DataFrame to avoid side effects
    df = df.copy()

    # If x, y, z columns exist, computes the 3D distance
    if ("x" in df) and ("y" in df) and ("z" in df):
        dist_3d = df[["x", "y", "z"]].diff()
        df["dist"] = np.sqrt(dist_3d.x**2 + dist_3d.y**2 + dist_3d.z**2).abs()
        # Assigns a generic path for all points
        df["path"] = "test"

    # If a "path" column exists, processes each path individually
    if "path" in df:
        # For each path, computes movement distance and filter out teleports or large jumps
        for path in df["path"].unique():
            # Blocks out values not on the current path
            pos = df["position"].copy() if "position" in df else None
            in_current_path = df["path"] == path
            if pos is not None:
                pos[~in_current_path] = np.nan
                # Calculates moved distance only for values on the current path
                df.loc[in_current_path, "dist"] = pos.diff().abs()

        # For each path, removes teleporting and calculate rolling speed
        for path in df["path"].unique():
            path_df = df.loc[df["path"] == path].copy()
            # Marks distances as NaN if not on this path (no longer needed since path_df is filtered)
            # Filters out too high movement distances likely corresponding to teleporting
            path_df.loc[path_df["dist"] > ignore_threshold, "dist"] = 0
            # Fills missing distances at the start of the path
            path_df["dist"] = path_df["dist"].fillna(0)
            # Converts time deltas to seconds, then compute instantaneous speed
            path_df["speed"] = path_df["dist"] / path_df["time"].dt.total_seconds().diff()
            path_df["speed"] = path_df["speed"].fillna(0)
            # Computes rolling speed based on the specified time window
            path_df = path_df.reset_index().set_index("time")
            path_df["speed"] = path_df["speed"].rolling(f"{window_size}ms", min_periods=1).mean()
            path_df = path_df.reset_index(drop=True)

            # Updates the main DataFrame with computed speeds
            # noinspection PyUnboundLocalVariable
            in_current_path = in_current_path.to_numpy()  # Prevents dtype mismatch error
            df.loc[in_current_path, "speed"] = path_df.loc[in_current_path, "speed"].to_numpy()

    else:
        message = (
            f"Unable to compute the movement speed for the input DataFrame. DataFrame must contain a 'path' column or "
            f"'x', 'y', 'z' columns along with 'time'."
        )
        console.error(message=message, error=KeyError)

    return df["speed"].to_numpy()
