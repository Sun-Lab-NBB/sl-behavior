from typing import Mapping, Sequence

import pandas as pd
from sl_shared_assets import SessionData

from .parse import (
    parse_gimbl_log as parse_gimbl_log,
    parse_trial_info as parse_trial_info,
    parse_period_info as parse_period_info,
    parse_session_events as parse_session_events,
)

DEFAULT_CUE_DEFINITIONS: tuple[dict[str, int | str], ...]

def _extract_cue_changes(
    path: pd.DataFrame,
    *,
    cue_definitions: Sequence[Mapping[str, int | str]] = ...,
    position_col: str = "position",
    time_col: str = "time_us",
) -> pd.DataFrame:
    """Generates that stores the sequence of wall cues experienced by the animal while running the session alongside
    the timestamp for each wall cue transition.

    Args:
        path: The Pandas DataFrame that stores the parsed session path information and contains at least 'position_col'
            and 'time_col'.
        cue_definitions: The ordered list or tuple of mappings with keys 'name', 'position_start', and 'position_end'.
            The default value of this argument corresponds to the standard 2‑AC track used in the Tyche project.
        position_col: The name of the column in 'path' that stores the linearized position values.
        time_col: The name of the column in 'path' that stores monotonic time stamps (in µs since UTC epoch onset).

    Returns:
        The Pandas DataFrame with columns 'time_us', 'vr_cue' and 'cue_name'.
    """

def extract_gimbl_data(session_data: SessionData, update_manifest: bool = False) -> None:
    """Reads and exports the data stored in the GIMBL .JSOn file to individual .feather files.

    This is a service function designed to process the legacy data from the Tyche dataset. It should not be used with
    modern Sun lab data and instead is purpose-built for reanalyzing the legacy Tyche dataset. Do not call this function
    unless you know what you are doing.

    Args:
        session_data: The SessionData instance for the session whose legacy log data needs to be processed.
        update_manifest: Determines whether to update (regenerate) the project manifest file for the processed
            session's project. This should always be enabled when working with remote compute server(s) to ensure that
            the project manifest file contains the most actual snapshot of the project's state.
    """
