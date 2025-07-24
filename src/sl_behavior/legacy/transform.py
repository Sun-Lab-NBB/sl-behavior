"""This module provides functions used to transform the Gimbl log data from the legacy format to the modern Sun lab
format.
"""

import pandas as pd
from ataraxis_base_utilities import console


def assign_frame_info(data: pd.DataFrame, frames: pd.DataFrame, remove_nan: bool = True) -> pd.DataFrame:
    """Joins indexed Gimbl log data with frame data to assign frame numbers to each Gimbl entry.

    This function merges the provided 'data' DataFrame with 'frames' DataFrame based on their time indices, ensuring
    each row in 'data' is assigned the corresponding Mesoscope 'frame' value.

    Args:
        data: A Pandas DataFrame that stores the Gimbl log data to assign frame indices to. Must contain the "time_us"
            column.
        frames: A Pandas DataFrame that stores parsed Mesoscope frame information. Must contain the "time_us" and the
            "frame" columns. The "time_us" column must be a datetime-like or timedelta type.
        remove_nan: Determines whether to remove entries outside the valid Mesoscope frame range (timesteps before the
            first frame or after the last frame).

    Returns:
        A new Pandas DataFrame with the added "frame" column, representing the Mesoscope frame index for each Gimbl
            data row. Rows outside the valid range are either dropped (if remove_nan is True) or assigned frame = -1
            (if remove_nan is False).
    """
    # Combines frames and data on the time index, then sorts
    frame_data = pd.concat(
        [frames.reset_index().set_index("time_us"), data.reset_index().set_index("time_us")]
    ).sort_index()

    # Identifies rows originally from 'data' (these lack frame info)
    idx = frame_data["frame"].isnull()

    # Forward-fills from frames to those rows
    frame_data["frame"] = frame_data["frame"].ffill()

    # Keeps only rows originally from the 'data'
    frame_data = frame_data[idx]

    # Drops any leftover "index" column if present
    if "index" in frame_data.columns:
        frame_data = frame_data.drop(columns="index")

    # Removes rows beyond the valid frame limits
    if remove_nan:
        frame_data = frame_data.dropna(subset=["frame"])
    else:
        # Assigns -1 if the index is outside the frame range
        frame_data["frame"] = frame_data["frame"].fillna(value=-1)
        if "level_0" in frame_data.columns:
            frame_data = frame_data.drop(columns="level_0")

    frame_data["frame"] = frame_data["frame"].astype("int32")
    frame_data = frame_data.reset_index()
    return frame_data


def forward_fill_missing_frame_info(
    frame_data: pd.DataFrame, frames: pd.DataFrame, nan_fill: bool = False, subset_columns: list[str] | None = None
) -> pd.DataFrame:
    """Forward-fills missing frame data by copying information from previous frame column entries.

    This function is used to ensure that each Mesoscope frame is bundled with Gimbl data. To do so, for each actor
    (identified by 'name'), expands the rows to cover all Mesoscope frames acquired during the session. Then either
    forward-fills (the default) the missing data or leaves it as None, depending on the 'nan_fill' argument.

    Args:
        frame_data: A Pandas DataFrame that stores the Gimbl log data with the "frame" columns. Typically, this
            DataFrame is sorted by ["frame", "name"] or can be re-sorted to that state.
        frames: A Pandas DataFrame that stores parsed Mesoscope frame information, which includes the number of frames
            and their timestamps.
        nan_fill: Determines whether to forward-fill missing values (if True) or to set them to None (if False).
        subset_columns: A list of columns for which to carry out the fill operation. This optional argument allows
            limiting the forward-fill operation to a subset of column.

    Returns:
        A Pandas DataFrame with the same columns as frame_data, potentially with extra entries to fill in gaps in frame
        data. The data in the output DataFrame is sorted by ["frame", "name"] before it is returned.
    """

    # If a column subset is not provided, works with all available columns
    if not subset_columns:
        subset_columns = frame_data.columns  # type: ignore

    # Prepares the data for processing all available frame x (unique) actor combinations
    num_frames = frames.shape[0]
    # Ensures 'frame_data' is multi-indexed consistently for iteration over each actor's data subset
    names = frame_data.reset_index()["name"].unique()

    for name in names:
        # Slices by current actor, re-indexes by 'frame'
        df = frame_data.loc[(slice(None), name), :].copy()
        df = df.reset_index().set_index("frame")

        # Creates a template with all frames and associated times for this actor
        template = pd.DataFrame(
            {"frame": range(num_frames), "name": name, "time_us": frames["time_us"].to_numpy()}
        ).set_index("frame")

        # Merges actor data with the template across all frames
        df = df.combine_first(template).sort_index()

        # Forward-fills or leaves NaN
        if not nan_fill:
            df[subset_columns] = df[subset_columns].ffill(axis=0)

        # Converts back to multi-index ["frame", "name"]
        df = df.reset_index().set_index(["frame", "name"])
        # Combines final results back into the main DataFrame
        frame_data = frame_data.combine_first(df)

    return frame_data.sort_index()


def add_ranged_timestamp_values(df: pd.DataFrame, timestamp_df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """Assigns values to rows in the input 'df' DataFrame based on whether the row's time falls within the time range
    in 'timestamp_df' DataFrame.

    If 'timestamp_df' has columns "time_start" and "time_end", each row in 'df' whose time is in [time_start, time_end]
    range receives the corresponding fields from that row of 'timestamp_df'.

    Note:
        This function does not remove the data that does not fall within the specified time range. It only adds new
        data.

    Args:
        df: The Pandas DataFrame to be augmented with additional data, must have a "time_us" column.
        timestamp_df: The Pandas DataFrame containing columns "time_start" and "time_end", which define the time
            ranges and the data to be copied into 'df' DataFrame.
        fields: A list of columns from 'timestamp_df' to merge into 'df' for rows whose 'time' falls in the specified
            [time_start, time_end] range.

    Returns:
        The original 'df' DataFrame with the specified columns is populated with additional data based on matching time
            ranges in 'df' and 'timestamp_df'. Columns are appended in the order encountered. Overlapping ranges in
            'timestamp_df' can result in 'df' data overwrites based on the later range in code iteration.

    Raises:
        ValueError: If any of the requested 'fields' are missing from the 'timestamp_df' DataFrame.
    """

    # Copies the dataframe to prevent changes by reference
    df = df.copy()

    # Remembers original column order
    original_columns = df.columns.to_list()

    # Verifies that requested 'fields' exist in 'timestamp_df'
    if not set(fields).issubset(timestamp_df.columns):
        message = (
            f"Unable to add ranged timestamp values to the input DataFrame, as some of the requested fields "
            f"({', '.join(fields)}) are missing from the source DataFrame provided as the 'timestamp_df' argument."
        )
        console.error(message=message, error=ValueError)

    # Adds any missing columns to 'df'
    missing_columns = list(set(fields).difference(set(df.columns)))
    for field in missing_columns:
        df[field] = None

    # Sorts timestamp_df by time_start for merge_asof
    timestamp_df = timestamp_df.sort_values("time_start")

    # Uses merge_asof to find the closest preceding time_start for each row in df
    df = pd.merge_asof(
        df.sort_values("time_us"),
        timestamp_df[["time_start", "time_end"] + fields].sort_values("time_start"),
        left_on="time_us",
        right_on="time_start",
        direction="backward",
    )

    # Filters rows where time_us falls outside the [time_start, time_end] range
    df = df[(df["time_us"] >= df["time_start"]) & (df["time_us"] <= df["time_end"])]

    # Drops helper columns and reorder fields
    df = df.drop(columns=["time_start", "time_end"])
    fields_in_order = [col for col in fields if col in df.columns]
    return df[original_columns + fields_in_order]


def convert_reward_data(reward_df: pd.DataFrame) -> pd.DataFrame:
    """Converts the input Gimbl reward DataFrame to the modern Sun Lab format.

    This service function makes legacy Tyche data compatible with the current data processing pipelines used in the Sun
    lab.

    Args:
        reward_df: A Pandas DataFrame that stores the reward data parsed from the Gimbl log file.

    Returns:
        The Polar DataFrame that stores reward data in the format matching the modern Sun lab standards.
    """

    # Converts the reward column to store the cumulative reward volume received by the animal at each time-point.
    reward_df["amount"] = reward_df["amount"].cumsum()

    # Renames columns to match the current Sun lab format.
    reward_df = reward_df.rename(columns={"sound_duration": "sound_duration_ms", "amount": "dispensed_water_volume_uL"})

    # Creates additional sound_off and valve_close rows for each sound_on == True epoch to mark the end of sound and
    # valve operation periods.
    for _, row in reward_df[reward_df["sound_on"]].iterrows():
        original_ts = row["time_us"]

        # Creates sound_off rows
        sound_off_row = row.copy()
        sound_off_row["sound_on"] = False
        # noinspection PyTypeChecker
        sound_off_row["time_us"] = original_ts + int(sound_off_row["sound_duration_ms"] * 1e3)

        # Creates valve_close rows
        valve_close_row = row.copy()
        # noinspection PyTypeChecker
        valve_close_row["time_us"] = original_ts + int(valve_close_row["valve_time"])
        if valve_close_row["time_us"] >= sound_off_row["time_us"]:
            valve_close_row["sound_on"] = False

        # Appends new rows
        reward_df = pd.concat([reward_df, pd.DataFrame([valve_close_row, sound_off_row])], ignore_index=True)

    # Drops unused 'helper' columns
    reward_df = reward_df.drop(columns=["valve_time", "sound_duration_ms"])

    # Sorts Dataframe by time
    reward_df = reward_df.sort_values(by="time_us")

    # Renames the sound column to match the current Sun lab naming convention. The convention changed between the
    # original implementation of this function and the 1.0.0 release.
    reward_df = reward_df.rename(columns={"sound_on": "tone_state"})

    return reward_df


def convert_lick_data(lick_df: pd.DataFrame) -> pd.DataFrame:
    """Converts the input Gimbl lick DataFrame to the modern Sun Lab format.

    This service function makes legacy Tyche data compatible with the current data processing pipelines used in the Sun
    lab.

    Args:
        lick_df: A Pandas DataFrame that stores the lick data parsed from the Gimbl log file.

    Returns:
        The Polar DataFrame that stores lick data in the format matching the modern Sun lab standards.
    """

    # Adds the lick_state column to the dataset. This is technically pointless, as Tyche data does not have the
    # capacity to resolve Lick duration, so it never has a data row where lick state is 'False'.
    lick_df = lick_df.copy()
    lick_df["lick_state"] = True
    return lick_df
