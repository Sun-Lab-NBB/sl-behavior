import os

import numpy as np
import pandas as pd


def export_gimbl_data(data, logs_df=None, out_dir: str = "."):
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
            data.position.frame.to_feather(os.path.join(out_dir, "position_frame_avg.feather"))

    if hasattr(data, "path"):
        if hasattr(data.path, "time") and isinstance(data.path.time, pd.DataFrame):
            data.path.time.to_feather(os.path.join(out_dir, "path_time.feather"))
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
        if hasattr(data, "spherical_controller_settings") and isinstance(data.spherical_controller_settings, pd.DataFrame):
            data.spherical_controller_settings.to_feather(os.path.join(out_dir, "spherical_controller_settings.feather"))
        if hasattr(data.spherical_controller, "time") and isinstance(data.spherical_controller.time, pd.DataFrame):
            data.spherical_controller.time.to_feather(os.path.join(out_dir, "spherical_controller_time.feather"))
        if hasattr(data.spherical_controller, "frame") and isinstance(data.spherical_controller.frame, pd.DataFrame):
            data.spherical_controller.frame.to_feather(os.path.join(out_dir, "spherical_controller_frame_avg.feather"))

    if logs_df is not None:
        # Filter and prepare trial start data
        start_trials = logs_df.loc[
            logs_df.msg == 'StartTrial',
            ['time_us', 'msg', 'data.status', 'data.rewardSet', 'data.rewardingCueId', 'data.trialNum']
        ].copy()

        # Filter and prepare trial end data
        end_trials = logs_df.loc[
            logs_df.msg == 'EndTrial',
            ['data.status', 'data.trialNum']
        ].copy()

        # Join start and end trial data on trial number
        trial_data = start_trials.join(
            end_trials.set_index('data.trialNum'),
            on='data.trialNum',
            rsuffix='_end'
        )

        # Update status column with end trial status
        trial_data['data.status'] = trial_data.pop('data.status_end')

        # Reset index and save to Feather file
        trial_data.reset_index(drop=True, inplace=True)
        trial_data.to_feather(os.path.join(out_dir, "trial_data.feather"))

        # Filter relevant rows and create a copy
        filtered_events = logs_df.loc[logs_df.msg.isin(['StartPeriod', 'StartTrial', 'EndTrial', 'EndPeriod'])].copy()

        # Update 'msg' column based on conditions
        conditions = [
            (filtered_events['data.type'] == 'TASK') & (filtered_events['msg'] == 'StartPeriod'),
            (filtered_events['data.type'] == 'TASK') & (filtered_events['msg'] == 'EndPeriod'),
            (filtered_events['data.type'] == 'DARK') & (filtered_events['msg'] == 'StartPeriod'),
            (filtered_events['data.type'] == 'DARK') & (filtered_events['msg'] == 'EndPeriod'),
            (filtered_events['msg'] == 'EndTrial')
        ]
        choices = ['StartTask', 'EndTask', 'StartRest', 'EndRest', 'StartTeleport']

        filtered_events['msg'] = np.select(conditions, choices, default=filtered_events['msg'])

        # Convert 'msg' column to categorical for memory efficiency
        filtered_events['msg'] = filtered_events['msg'].astype('category')

        # Select relevant columns
        filtered_events = filtered_events[['time_us', 'msg']]

        filtered_events.reset_index(drop=True, inplace=True)
        filtered_events.to_feather(os.path.join(out_dir, "session_data.feather"))
