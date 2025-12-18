from pathlib import Path

import numpy as np
from numpy.typing import NDArray as NDArray
from sl_shared_assets import (
    GasPuffTrial as GasPuffTrial,
    WaterRewardTrial as WaterRewardTrial,
    MesoscopeExperimentConfiguration,
)

_CUE_SEQUENCE_MIN_LENGTH: int
_SYSTEM_STATE_CODE: int
_RUNTIME_STATE_CODE: int
_REINFORCING_GUIDANCE_STATE_CODE: int
_AVERSIVE_GUIDANCE_STATE_CODE: int
_DISTANCE_SNAPSHOT_CODE: int

def _prepare_motif_data(
    trial_motifs: list[NDArray[np.uint8]], trial_distances: list[float]
) -> tuple[NDArray[np.uint8], NDArray[np.int32], NDArray[np.int32], NDArray[np.int32], NDArray[np.float32]]: ...
def _decompose_sequence_numba_flat(
    cue_sequence: NDArray[np.uint8],
    motifs_flat: NDArray[np.uint8],
    motif_starts: NDArray[np.int32],
    motif_lengths: NDArray[np.int32],
    motif_indices: NDArray[np.int32],
    max_trials: int,
) -> tuple[NDArray[np.int32], int]: ...
def _decompose_multiple_cue_sequences_into_trials(
    experiment_configuration: MesoscopeExperimentConfiguration,
    cue_sequences: list[NDArray[np.uint8]],
    distance_breakpoints: list[np.float64],
) -> tuple[NDArray[np.int32], NDArray[np.float64]]: ...
def _decompose_cue_sequence_into_trials(
    experiment_configuration: MesoscopeExperimentConfiguration, cue_sequence: NDArray[np.uint8]
) -> tuple[NDArray[np.int32], NDArray[np.float64]]: ...
def _process_trial_sequence(
    experiment_configuration: MesoscopeExperimentConfiguration,
    trial_types: NDArray[np.int32],
    trial_distances: NDArray[np.float64],
) -> tuple[NDArray[np.uint8], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]: ...
def _extract_mesoscope_vr_data(
    log_path: Path, output_directory: Path, experiment_configuration: MesoscopeExperimentConfiguration | None = None
) -> None: ...
def process_runtime_data(session_path: Path) -> None: ...
