import pandas as pd

def assign_frame_info(data: pd.DataFrame, frames: pd.DataFrame, remove_nan: bool = True) -> pd.DataFrame:
    """Joins indexed Gimbl log data with frame data to assign frame numbers to each Gimbl entry.

    This function merges the provided \'data\' DataFrame with \'frames\' DataFrame based on their time indices, ensuring
    each row in \'data\' is assigned the corresponding Mesoscope \'frame\' value.

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

def forward_fill_missing_frame_info(
    frame_data: pd.DataFrame, frames: pd.DataFrame, nan_fill: bool = False, subset_columns: list[str] | None = None
) -> pd.DataFrame:
    """Forward-fills missing frame data by copying information from previous frame column entries.

    This function is used to ensure that each Mesoscope frame is bundled with Gimbl data. To do so, for each actor
    (identified by \'name\'), expands the rows to cover all Mesoscope frames acquired during the session. Then either
    forward-fills (the default) the missing data or leaves it as None, depending on the \'nan_fill\' argument.

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

def add_ranged_timestamp_values(df: pd.DataFrame, timestamp_df: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """Assigns values to rows in the input \'df\' DataFrame based on whether the row\'s time falls within the time range
    in \'timestamp_df\' DataFrame.

    If \'timestamp_df\' has columns "time_start" and "time_end", each row in \'df\' whose time is in [time_start, time_end]
    range receives the corresponding fields from that row of \'timestamp_df\'.

    Note:
        This function does not remove the data that does not fall within the specified time range. It only adds new
        data.

    Args:
        df: The Pandas DataFrame to be augmented with additional data, must have a "time_us" column.
        timestamp_df: The Pandas DataFrame containing columns "time_start" and "time_end", which define the time
            ranges and the data to be copied into \'df\' DataFrame.
        fields: A list of columns from \'timestamp_df\' to merge into \'df\' for rows whose \'time\' falls in the specified
            [time_start, time_end] range.

    Returns:
        The original \'df\' DataFrame with the specified columns is populated with additional data based on matching time
            ranges in \'df\' and \'timestamp_df\'. Columns are appended in the order encountered. Overlapping ranges in
            \'timestamp_df\' can result in \'df\' data overwrites based on the later range in code iteration.

    Raises:
        ValueError: If any of the requested \'fields\' are missing from the \'timestamp_df\' DataFrame.
    """

def convert_reward_data(reward_df: pd.DataFrame) -> pd.DataFrame:
    """Converts the input Gimbl reward DataFrame to the modern Sun Lab format.

    This service function makes legacy Tyche data compatible with the current data processing pipelines used in the Sun
    lab.

    Args:
        reward_df: A Pandas DataFrame that stores the reward data parsed from the Gimbl log file.

    Returns:
        The Polar DataFrame that stores reward data in the format matching the modern Sun lab standards.
    """

def convert_lick_data(lick_df: pd.DataFrame) -> pd.DataFrame:
    """Converts the input Gimbl lick DataFrame to the modern Sun Lab format.

    This service function makes legacy Tyche data compatible with the current data processing pipelines used in the Sun
    lab.

    Args:
        lick_df: A Pandas DataFrame that stores the lick data parsed from the Gimbl log file.

    Returns:
        The Polar DataFrame that stores lick data in the format matching the modern Sun lab standards.
    """
