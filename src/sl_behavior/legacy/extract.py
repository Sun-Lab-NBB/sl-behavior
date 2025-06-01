"""This module provides utility functions used to calculate movement speed and other metrics from position data stored
in DataFrames extracted from Gimbl logs.
"""

from typing import Any

import polars as pl
from numpy.typing import NDArray
from ataraxis_base_utilities import console


def movement_speed(df: pl.DataFrame, window_size: int = 100, ignore_threshold: float = 20) -> NDArray[Any]:
    """Calculates the rolling average movement speed in centimeters per second (cm/s) from the input DataFrame.

    The DataFrame must contain either columns named "x", "y", "z", "time", or columns named "position", "path", "time".

    If "x", "y", and "z" are present, the function automatically calculates the distance in 3D space for each frame and
    assigns them to a temporary path "test". Otherwise, if "path" is present, it processes each path independently.

    Teleport artifacts or extremely large movements beyond the specified threshold are set to zero before rolling
    computation. The rolling window is indexed by the time column, which must be a polars Datetime column.

    Args:
        df: A Polars DataFrame containing the required columns ("x", "y", "z", "time", or "position", "path", "time").
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
    # Preserves original order
    df = df.with_row_index("_original_order")

    # If x, y, z columns exist, computes the 3D distance
    if all(col in df.columns for col in ["x", "y", "z"]):
        # Calculates 3D distance between consecutive points
        df = df.with_columns(
            [
                (
                    (pl.col("x") - pl.col("x").shift(1)) ** 2
                    + (pl.col("y") - pl.col("y").shift(1)) ** 2
                    + (pl.col("z") - pl.col("z").shift(1)) ** 2
                )
                .sqrt()
                .alias("dist"),
                # Assigns a generic path name for all points
                pl.lit("test").alias("path"),
            ]
        )

    # Checks for required columns
    if "path" not in df.columns:
        message = (
            f"Unable to compute the movement speed for the input DataFrame. DataFrame must contain a 'path' column or "
            f"'x', 'y', 'z' columns along with 'time'."
        )
        console.error(message=message, error=KeyError)

    # Calculates distance from position if needed
    if "dist" not in df.columns and "position" in df.columns:
        # Sorts by path and time, then calculates distance within each path
        df = df.sort(["path", "time"]).with_columns([pl.col("position").diff().over("path").abs().alias("dist")])

    # Calculates the movement speed at each frame
    result = (
        df.sort(["path", "time"])
        .with_columns(
            [
                # Filters out teleport artifacts
                pl.when(pl.col("dist") > ignore_threshold)
                .then(0.0)
                .otherwise(pl.col("dist"))
                .fill_null(0.0)
                .alias("dist_filtered"),
                # Calculates time differences in seconds within each path
                pl.col("time").diff().over("path").dt.total_milliseconds().truediv(1000.0).alias("time_diff_seconds"),
            ]
        )
        .with_columns(
            [
                # Calculates instantaneous speed
                pl.when(pl.col("time_diff_seconds").gt(0))
                .then(pl.col("dist_filtered") / pl.col("time_diff_seconds"))
                .otherwise(0.0)
                .fill_null(0.0)
                .alias("speed_instant")
            ]
        )
        .with_columns(
            [
                # Calculates rolling speed within each path
                pl.col("speed_instant")
                .rolling_mean_by("time", window_size=f"{window_size}ms", min_periods=1, closed="right")
                .over("path")
                .alias("speed")
            ]
        )
        .sort("_original_order")
    )

    return result["speed"].to_numpy()
