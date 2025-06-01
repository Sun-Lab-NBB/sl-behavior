from __future__ import annotations

import os
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from .parse import (
    parse_trial_info,
    process_gimbl_df,
    parse_period_info,
    parse_session_events,
)

# Default cue table (immutable so it can be re‑used across calls)
DEFAULT_CUE_DEFINITIONS: tuple[dict[str, int | str], ...] = (
    {"name": "Gray_60cm", "position_start": 0, "position_end": 60},
    {"name": "Indicator", "position_start": 60, "position_end": 100},
    {"name": "Gray_30cm", "position_start": 100, "position_end": 130},
    {"name": "R1", "position_start": 130, "position_end": 150},
    {"name": "Gray_30cm", "position_start": 150, "position_end": 180},
    {"name": "R2", "position_start": 180, "position_end": 200},
    {"name": "Gray_30cm", "position_start": 200, "position_end": 230},
    {"name": "Teleportation", "position_start": 230, "position_end": 231},
)


def _extract_cue_changes(
    path: pd.DataFrame,
    *,
    cue_definitions: Sequence[Mapping[str, int | str]] = DEFAULT_CUE_DEFINITIONS,
    position_col: str = "position",
    time_col: str = "time_us",
) -> pd.DataFrame:
    """Return a compact table with one row per cue transition.

    Args:
        path: DataFrame containing at least ``position_col`` and ``time_col``.
              Typically this is ``data.path.time`` from your pipeline.
        cue_definitions: Ordered list/tuple of mappings with keys
            ``name``, ``position_start`` and ``position_end``.
            The default corresponds to the standard 2‑AC track.
        position_col: Column in *path* that stores linearised position values.
        time_col: Column in *path* that stores monotonic time stamps (µs).

    Returns:
        DataFrame with columns
        ``time_us`` – time at which the cue became active
        ``vr_cue`` – categorical integer code (stable across calls)
        ``cue_name`` – human‑readable cue identifier
    """
    # ---------------------------- validation --------------------------------- #
    missing = {c for c in (position_col, time_col) if c not in path.columns}
    if missing:
        raise KeyError(f"`path` is missing required column(s): {missing}")

    # ----------------------------- cue table --------------------------------- #
    cues_df = pd.DataFrame(cue_definitions, copy=False)
    if not {"name", "position_start", "position_end"}.issubset(cues_df.columns):
        msg = "`cue_definitions` must supply 'name', 'position_start' and 'position_end' keys."
        raise ValueError(msg)

    # Stable integer labels for fast look‑ups
    cues_df["vr_cue"] = cues_df["name"].astype("category").cat.codes

    # ------------------------------ binning ---------------------------------- #
    positions = path[position_col].to_numpy(copy=False)
    bin_edges = cues_df["position_start"].to_numpy(copy=False)
    cue_bins = np.digitize(positions, bin_edges, right=False)
    bin_changes = np.diff(cue_bins)

    change_idx = np.where(bin_changes != 0)[0] + 1
    change_idx = np.insert(change_idx, 0, 0)

    # -------------------------- assemble result ----------------------------- #
    return pd.DataFrame(
        {
            "time_us": path[time_col].iloc[change_idx].to_numpy(),
            "vr_cue": cues_df["vr_cue"].iloc[cue_bins[change_idx] - 1].values,
            "cue_name": cues_df["name"].iloc[cue_bins[change_idx] - 1].values,
        }
    ).reset_index(drop=True)


def export_gimbl_data(logs_df, out_dir: str = "."):
    """Exports each table from 'data' (returned by parse_gimbl_log) to individual Feather files.

    Args:
        data (GimblData): Parsed GimblData object containing various DataFrames.
        out_dir (str): Destination folder for Feather files.

    Example:
        # >>> from sl_behavior.legacy.parse import parse_gimbl_log
        # >>> df, data = parse_gimbl_log("path/to/log.json")
        # >>> export_gimbl_data(df, out_dir='./Results')
    """
    _, data = process_gimbl_df(logs_df)

    os.makedirs(out_dir, exist_ok=True)

    if hasattr(data, "frames") and isinstance(data.frames, pd.DataFrame):
        data.frames.to_feather(os.path.join(out_dir, "frames.feather"))

    if hasattr(data, "position"):
        if hasattr(data.position, "time") and isinstance(data.position.time, pd.DataFrame):
            data.position.time.to_feather(os.path.join(out_dir, "position_time.feather"))
        if hasattr(data.position, "frame") and isinstance(data.position.frame, pd.DataFrame):
            data.position.frame.to_feather(os.path.join(out_dir, "position_frame_avg.feather"))

    if hasattr(data, "path"):
        if hasattr(data.path, "time") and isinstance(data.path.time, pd.DataFrame):
            data.path.time.to_feather(os.path.join(out_dir, "path_time.feather"))

            # encoder data
            all_pos = data.path.time.position.to_numpy()
            all_pos = np.clip(all_pos, 0, 230)
            all_pos_diff = np.diff(all_pos, prepend=0)
            all_pos_diff[all_pos_diff < 0] = 0
            all_pos_csum = np.cumsum(all_pos_diff)

            encoder_data = pd.DataFrame(
                {
                    "time_us": data.path.time.time_us.to_numpy(),
                    "traveled_distance_cm": all_pos_csum,
                }
            )

            encoder_data.to_feather(os.path.join(out_dir, "encoder_data.feather"))

            cue_data = _extract_cue_changes(data.path.time, cue_definitions=DEFAULT_CUE_DEFINITIONS)
            cue_data.to_feather(os.path.join(out_dir, "cue_data.feather"))

        if hasattr(data.path, "frame") and isinstance(data.path.frame, pd.DataFrame):
            data.path.frame.to_feather(os.path.join(out_dir, "path_frame_avg.feather"))

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
            data.linear_controller.frame.to_feather(os.path.join(out_dir, "linear_controller_frame_avg.feather"))

    if hasattr(data, "spherical_controller"):
        if hasattr(data, "spherical_controller_settings") and isinstance(
            data.spherical_controller_settings, pd.DataFrame
        ):
            data.spherical_controller_settings.to_feather(
                os.path.join(out_dir, "spherical_controller_settings.feather")
            )
        if hasattr(data.spherical_controller, "time") and isinstance(data.spherical_controller.time, pd.DataFrame):
            data.spherical_controller.time.to_feather(os.path.join(out_dir, "spherical_controller_time.feather"))
        if hasattr(data.spherical_controller, "frame") and isinstance(data.spherical_controller.frame, pd.DataFrame):
            data.spherical_controller.frame.to_feather(os.path.join(out_dir, "spherical_controller_frame_avg.feather"))

    trial_data = parse_trial_info(logs_df)
    trial_data.to_feather(os.path.join(out_dir, "trial_data.feather"))

    filtered_events = parse_session_events(logs_df)
    filtered_events.to_feather(os.path.join(out_dir, "session_data.feather"))

    period_data = parse_period_info(logs_df)
    period_data.to_feather(os.path.join(out_dir, "period_data.feather"))
