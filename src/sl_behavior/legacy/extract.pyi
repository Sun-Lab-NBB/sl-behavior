from typing import Any

import pandas as pd
from numpy.typing import NDArray as NDArray

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
