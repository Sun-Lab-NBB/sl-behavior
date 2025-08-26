from pathlib import Path

from numba import prange as prange
import numpy as np
from _typeshed import Incomplete
from numpy.typing import NDArray as NDArray
from sl_shared_assets import (
    ExperimentTrial as ExperimentTrial,
    MesoscopeExperimentConfiguration,
)

_supported_systems: Incomplete
_supported_sessions: Incomplete

def _prepare_motif_data(
    trial_motifs: list[NDArray[np.uint8]], trial_distances: list[float]
) -> tuple[NDArray[np.uint8], NDArray[np.int32], NDArray[np.int32], NDArray[np.int32], NDArray[np.float32]]:
    """Prepares the flattened trial motif data to speed up the cue-sequence-to-trial decomposition (conversion) process.

    Args:
        trial_motifs: A list of trial motifs (wall cue sequences) used by the processed session, where each sequence
            is stored as a numpy array.
        trial_distances: A list of trial motif distances in centimeters. Should match the order of items inside the
            trial_motifs list.

    Returns:
        A tuple containing five elements. The first element is a flattened array that stores all trial motifs. The
        second element is an array that stores the starting indices of each motif in the flat array. The third element
        is an array that stores the length of each motif. The fourth element is an array that stores the original
        indices of motifs before sorting. The fifth element is an array of trial distances in centimeters.
    """

def _decompose_sequence_numba_flat(
    cue_sequence: NDArray[np.uint8],
    motifs_flat: NDArray[np.uint8],
    motif_starts: NDArray[np.int32],
    motif_lengths: NDArray[np.int32],
    motif_indices: NDArray[np.int32],
    max_trials: int,
) -> tuple[NDArray[np.int32], int]:
    """Decomposes a long sequence of Virtual Reality (VR) wall cues into individual trial motifs.

    This is a worker function used by the main _decompose_multiple_cue_sequences_into_trials() function to speed up
    sequence decomposition via numba-acceleration.

    Args:
        cue_sequence: The full cue sequence to decompose.
        motifs_flat: All motifs concatenated into a single 1D array.
        motif_starts: Starting index of each motif in motifs_flat.
        motif_lengths: The length of each motif.
        motif_indices: Original indices of motifs (before sorting).
        max_trials: The maximum number of trials that can make up the cue sequence.

    Returns:
        A tuple of two elements. The first element stores the array of trial type-indices (the sequence of trial
        type indices). The second element stores the total number of trials extracted from the cue sequence.
    """

def _decompose_multiple_cue_sequences_into_trials(
    experiment_configuration: MesoscopeExperimentConfiguration,
    cue_sequences: list[NDArray[np.uint8]],
    distance_breakpoints: list[np.float64],
) -> tuple[NDArray[np.int32], NDArray[np.float64]]:
    """Decomposes multiple Virtual Reality (VR) task wall cue sequences into a unified sequence of trials.

    This function handles cases where the original sequence was interrupted and a new sequence was generated. It uses
    distance breakpoints to stitch sequences together correctly.

    Args:
        experiment_configuration: The initialized ExperimentConfiguration instance for which to parse the trial data.
        cue_sequences: A list of cue sequences in the order they were used during runtime.
        distance_breakpoints: A list of cumulative distances (in centimeters) at which each sequence ends. Should have
            the same number of elements as the number of cue sequences - 1.

    Returns:
        A tuple of two elements. The first element is an array of trial type indices stored in the order encountered at
        runtime. The second element is an array of cumulative distances at the end of each trial.

    Raises:
        ValueError: If the number of breakpoints doesn't match the number of sequences - 1.
        RuntimeError: If the function is not able to fully decompose any of the cue sequences.
    """

def _decompose_cue_sequence_into_trials(
    experiment_configuration: MesoscopeExperimentConfiguration, cue_sequence: NDArray[np.uint8]
) -> tuple[NDArray[np.int32], NDArray[np.float64]]:
    """Decomposes a single Virtual Reality task wall cue sequence into a sequence of trials.

    This is a convenience wrapper around the _decompose_multiple_cue_sequences_into_trials() function to use when
    working with runtimes that only used a single wall cue sequence. Since multiple sequences are only present in
    runtimes that encountered issues at runtime, this function is typically used during most data processing runtimes.

    Args:
        experiment_configuration: The initialized ExperimentConfiguration instance for which to parse the trial data.
        cue_sequence: The cue sequence to decompose into trials.

    Returns:
        A tuple of two elements. The first element is an array of trial type indices stored in the order encountered at
        runtime. The second element is an array of cumulative distances at the end of each trial.

    Raises:
        RuntimeError: If the function is not able to fully decompose the cue sequence.
    """

def _process_trial_sequence(
    experiment_configuration: MesoscopeExperimentConfiguration,
    trial_types: NDArray[np.int32],
    trial_distances: NDArray[np.float64],
) -> tuple[NDArray[np.uint8], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Processes the sequence of trials experienced by the animal during runtime to extract trial metadata information.

    This function processes the trial sequences generated by the _decompose_cue_sequence_into_trials() and
    _decompose_multiple_cue_sequences_into_trials() function. The metadata extracted by this function is used to
    support trial-based data analysis in the sl-forgery library.

    Args:
        experiment_configuration: The initialized ExperimentConfiguration instance for which to process the trial
            sequence data.
        trial_types: A NumPy array that stores the indices used to query the trial data for each trial experienced by
            the animal at runtime. The indices are used to query each trial's ExperimentTrial instance from the
            ExperimentConfiguration instance.
        trial_distances: A NumPy array that stores the cumulative traveled distance, in centimeters, at which the animal
            fully completed the trial at runtime. The elements in this array use the same order as elements in the
            trial_types array.

    Returns:
        A tuple of five NumPy arrays. The first array stores the IDs of the cues experienced by the animal at runtime.
        The second array stores the total cumulative distance, in centimeters, traveled by the animal at the onset
        of each cue stored in the first array. The third array stores the cumulative distance traveled by the animal
        when it entered each trial's reward zone. The fourth array stores the cumulative distance traveled by the animal
        when it left each trial's reward zone. The fifth array stores the cumulative distance traveled by the animal
        during each trial when it collided with the invisible wall used to trigger water delivery in 'guided' mode.

    """

def _extract_mesoscope_vr_data(
    log_path: Path, output_directory: Path, experiment_configuration: MesoscopeExperimentConfiguration | None = None
) -> None:
    """Reads the Mesoscope-VR acquisition system .npz log file and extracts acquisition system and runtime (task) data
    as uncompressed .feather files.

    This worker function is specifically designed to process the data logged by the Mesoscope-VR acquisition systems.
    It does not work for any other Sun lab data acquisition system.

    Args:
        log_path: The path to the .npz archive containing the Mesoscope-VR acquisition system data to parse.
        output_directory: The path to the directory where to save the extracted data as uncompressed .feather files.
        experiment_configuration: The ExperimentConfiguration class for the processed session, if the processed session
            is an experiment.
    """

def process_runtime_data(
    session_path: Path,
    manager_id: int,
    job_count: int,
    reset_tracker: bool = False,
    processed_data_root: Path | None = None,
) -> None:
    """Reads the target session's data acquisition system .npz log file and extracts acquisition system and runtime
    (task) data as uncompressed .feather files.

    This function is used to process the log archives generated by any data acquisition system used in the Sun lab. It
    assumes that the data was logged using the assets from the sl-experiment library.

    Notes:
        This function statically assumes that the acquisition system log file uses the id '1'.

    Args:
        session_path: The path to the session directory for which to process the acquisition system log file.
        manager_id: The unique identifier of the manager process that manages the log processing runtime.
        job_count: The total number of jobs executed as part of the behavior processing pipeline that calls this
            function.
        reset_tracker: Determines whether to reset the tracker file before executing the runtime. This allows
            recovering from deadlocked runtimes, but otherwise should not be used to ensure runtime safety.
        processed_data_root: The absolute path to the directory where processed data from all projects is stored, if
            different from the root directory provided as part of the 'session_path' argument.
    """
