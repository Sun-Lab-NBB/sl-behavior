from typing import Any
from pathlib import Path

import numpy as np
from _typeshed import Incomplete
from numpy.typing import NDArray as NDArray
from sl_shared_assets import SessionData, MesoscopeHardwareState, MesoscopeExperimentConfiguration
from ataraxis_communication_interface import ExtractedModuleData

_supported_acquisition_systems: Incomplete
_supported_session_types: Incomplete

def _prepare_motif_data(
    trial_motifs: list[NDArray[np.uint8]], trial_distances: list[float]
) -> tuple[NDArray[np.uint8], NDArray[np.int32], NDArray[np.int32], NDArray[np.int32], NDArray[np.float32]]:
    """Prepares the flattened trial motif data for faster cue sequence-to-trial decomposition (conversion).

    Args:
        trial_motifs: A list of trial motifs (wall cue sequences) used by the processed session, in the format of
            numpy arrays.
        trial_distances: A list of trial distances in centimeters. Should match the order of items inside the
            trial_motifs list.

    Returns:
        A tuple containing five elements. The first element is a flattened array of all motifs. The second
        element is an array that stores the starting indices of each motif in the flat array. The third element is
        an array that stores the length of each motif. The fourth element is an array that stores the original
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

    This is a worker function used to speed up decomposition via numba-acceleration.

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

    Handles cases where the original sequence was interrupted and a new sequence was generated. Uses distance
    breakpoints to stitch sequences together correctly.

    Args:
        experiment_configuration: The initialized ExperimentConfiguration instance for which to parse the trial data.
        cue_sequences: A list of cue sequences in the order they were used during runtime.
        distance_breakpoints: A list of cumulative distances (in centimeters) at which each sequence ends. Should have
            the same number of elements as the number of cue sequences - 1.

    Returns:
        A tuple of two elements. The first element is an array of trial type indices in the order encountered at
        runtime. The second element is an array of cumulative distances at the end of each trial.

    Raises:
        ValueError: If the number of breakpoints doesn't match the number of sequences - 1.
        RuntimeError: If the function is not able to fully decompose any of the cue sequences.
    """

def _decompose_cue_sequence_into_trials(
    experiment_configuration: MesoscopeExperimentConfiguration, cue_sequence: NDArray[np.uint8]
) -> tuple[NDArray[np.int32], NDArray[np.float64]]:
    """Decomposes a single Virtual Reality task wall cue sequence into a sequence of trials.

    This is a convenience wrapper around _decompose_multiple_cue_sequences_into_trials for backward compatibility when
    working with runtimes that only used a single wall cue sequence. Since multiple sequences are only present in
    runtimes that encountered issues at runtime, this function should, in fact, be used during most data processing
    runtimes.

    Args:
        experiment_configuration: The initialized ExperimentConfiguration instance for which to parse the trial data.
        cue_sequence: The cue sequence to decompose into trials.

    Returns:
        A tuple that contains two elements. The first element is an array of trial type indices in the order encountered
        at runtime. The second element is an array of cumulative distances at the end of each trial.

    Raises:
        RuntimeError: If the function is not able to fully decompose the cue sequence.
    """

def _process_trial_sequence(
    experiment_configuration: MesoscopeExperimentConfiguration,
    trial_types: NDArray[np.int32],
    trial_distances: NDArray[np.float64],
) -> tuple[NDArray[np.uint8], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Processes the sequence of trials experienced by the animal during runtime to extract various trial metadata
    information.

    This function uses the sequence of trials generated by _decompose_cue_sequence_into_trials() and
    _decompose_multiple_cue_sequences_into_trials() to extract various trial-related metadata. It generates multiple
    data sources critical for trial-based analyses.

    Args:
        experiment_configuration: The initialized ExperimentConfiguration instance for which to generate the
            cue-distance data.
        trial_types: A NumPy array that stores the indices of each trial type experienced by the animal at runtime. The
            indices are used to query the trial data from the ExperimentConfiguration instance.
        trial_distances: A NumPy array that stores the actual cumulative distance, in centimeters, at which the animal
            fully completed the trial at runtime. The entries in this array should be in the same order as indices in
            the trial_types array.

    Returns:
        A tuple of five NumPy arrays. The first array stores the IDs of the cues experienced by the animal at runtime.
        The second array stores the total cumulative distance, in centimeters, traveled by the animal at the onset
        of each cue stored in the first array. The third array stores the cumulative distance traveled by the animal
        when it entered each reward zone encountered at runtime. The fourth array stores the cumulative distance
        traveled by the animal when it exited each reward zone encountered at runtime. The fifth array stores the
        cumulative distance at the onset of each trial experienced by the animal at runtime.

    """

def _interpolate_data(
    timestamps: NDArray[np.uint64],
    data: NDArray[np.integer[Any] | np.floating[Any]],
    seed_timestamps: NDArray[np.uint64],
    is_discrete: bool,
) -> NDArray[np.signedinteger[Any] | np.unsignedinteger[Any] | np.floating[Any]]:
    """Interpolates data values for the provided seed timestamps.

    Primarily, this service function is used to time-align different datastreams from the same source. For example, the
    Valve module generates both the solenoid valve data and the auditory tone data, which is generated at non-matching
    rates. This function is used to equalize the data sampling rate between the two data streams, allowing to output
    the data as .feather file.

    Notes:
        This function expects seed_timestamps and timestamps arrays to be monotonically increasing.

        Discrete interpolated data will be returned as an array with the same datatype as the input data. Continuous
        interpolated data will always use float_64 datatype.

    Args:
        timestamps: The one-dimensional numpy array that stores the timestamps for the source data.
        data: The one-dimensional numpy array that stores the source datapoints.
        seed_timestamps: The one-dimensional numpy array that stores the timestamps for which to interpolate the data
            values.
        is_discrete: A boolean flag that determines whether the data is discrete or continuous.

    Returns:
        A numpy NDArray with the same dimension as the seed_timestamps array that stores the interpolated data values.
    """

def _parse_encoder_data(
    extracted_module_data: ExtractedModuleData, output_directory: Path, cm_per_pulse: np.float64
) -> None:
    """Extracts and saves the data acquired by the EncoderModule during runtime as a .feather file.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        cm_per_pulse: The conversion factor to translate raw encoder pulses into distance in centimeters.
    """

def _parse_ttl_data(extracted_module_data: ExtractedModuleData, output_directory: Path, log_name: str) -> None:
    """Extracts and saves the data acquired by the TTLModule during runtime as a .feather file.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        log_name: The unique name to use for the output .feather file. Since we use more than a single TTLModule
            instance, it may be necessary to distinguish different TTL log files from each other by using unique file
            names to store the parsed data.
    """

def _parse_break_data(
    extracted_module_data: ExtractedModuleData,
    output_directory: Path,
    maximum_break_strength: np.float64,
    minimum_break_strength: np.float64,
) -> None:
    """Extracts and saves the data acquired by the BreakModule during runtime as a .feather file.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        maximum_break_strength: The maximum torque of the break in Newton centimeters.
        minimum_break_strength: The minimum torque of the break in Newton centimeters.

    Notes:
        This method assumes that the break was used in the absolute force mode. It does not extract variable
        breaking power data.
    """

def _parse_valve_data(
    extracted_module_data: ExtractedModuleData,
    output_directory: Path,
    scale_coefficient: np.float64,
    nonlinearity_exponent: np.float64,
) -> None:
    """Extracts and saves the data acquired by the ValveModule during runtime as a .feather file.

    Notes:
        Unlike other processing methods, this method generates a .feather dataset with 3 columns: time, dispensed
        water volume, and the state of the tone buzzer.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        scale_coefficient: Stores the scale coefficient used in the fitted power law equation that translates valve
            pulses into dispensed water volumes.
        nonlinearity_exponent: Stores the nonlinearity exponent used in the fitted power law equation that
            translates valve pulses into dispensed water volumes.
    """

def _parse_lick_data(
    extracted_module_data: ExtractedModuleData, output_directory: Path, lick_threshold: np.uint16
) -> None:
    """Extracts and saves the data acquired by the LickModule during runtime as a .feather file.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        lick_threshold: The voltage threshold for detecting the interaction with the sensor as a lick.

    Notes:
        The extraction classifies lick events based on the lick threshold used by the class during runtime. The
        time-difference between consecutive ON and OFF event edges corresponds to the time, in microseconds, the
        tongue maintained contact with the lick tube. This may include both the time the tongue physically
        touched the tube and the time there was a conductive fluid bridge between the tongue and the lick tube.

        In addition to classifying the licks and providing binary lick state data, the extraction preserves the raw
        12-bit ADC voltages associated with each lick. This way, it is possible to spot issues with the lick detection
        system by applying a different lick threshold from the one used at runtime, potentially augmenting data
        analysis.
    """

def _parse_torque_data(
    extracted_module_data: ExtractedModuleData, output_directory: Path, torque_per_adc_unit: np.float64
) -> None:
    """Extracts and saves the data acquired by the TorqueModule during runtime as a .feather file.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        torque_per_adc_unit: The conversion actor used to translate ADC units recorded by the torque sensor into
            the torque in Newton centimeter, applied by the animal to the wheel.

    Notes:
        Despite this method trying to translate the detected torque into Newton centimeters, it may not be accurate.
        Partially, the accuracy of the translation depends on the calibration of the interface class, which is very
        hard with our current setup. The accuracy also depends on the used hardware, and currently our hardware is
        not very well suited for working with millivolt differential voltage levels used by the sensor to report
        torque. Therefore, currently, it is best to treat the torque data extracted from this module as a very rough
        estimate of how active the animal is at a given point in time.
    """

def _parse_screen_data(extracted_module_data: ExtractedModuleData, output_directory: Path, initially_on: bool) -> None:
    """Extracts and saves the data acquired by the ScreenModule during runtime as a .feather file.

    Args:
        extracted_module_data: The ExtractedModuleData instance that stores the data logged by the module during
            runtime.
        output_directory: The path to the directory where to save the parsed data as a .feather file.
        initially_on: Communicates the initial state of the screen at module interface initialization. This is used
            to determine the state of the screens after each processed screen toggle signal.

    Notes:
        This extraction method works similar to the TTLModule method. This is intentional, as ScreenInterface is
        essentially a group of 3 TTLModules.
    """

def _process_camera_timestamps(log_path: Path, output_path: Path) -> None:
    """Reads the log .npz archive specified by the log_path and extracts the camera frame timestamps
    as a Polars Series saved to the output_path as a Feather file.

    Args:
        log_path: The path to the .npz log archive to be parsed.
        output_path: The path to the output .feather file where to save the extracted data.
    """

def _process_runtime_data(
    log_path: Path, output_directory: Path, experiment_configuration: MesoscopeExperimentConfiguration | None = None
) -> None:
    """Extracts the acquisition system states, experiment states, and any additional system-specific data from the log
    generated during an experiment runtime and saves the extracted data as Polars DataFrame .feather files.

    This extraction method functions similar to camera log extraction and hardware module log extraction methods. The
    key difference is that this function contains additional arguments that allow specializing it for extracting the
    data generated by different acquisition systems used in the Sun lab.

    Args:
        log_path: The path to the .npz archive containing the VR and experiment data to parse.
        output_directory: The path to the directory where to save the extracted data as .feather files.
        experiment_configuration: The ExperimentConfiguration class for the runtime, if the processed runtime is an
            experiment.
    """

def _process_actor_data(log_path: Path, output_directory: Path, hardware_state: MesoscopeHardwareState) -> None:
    """Extracts the data logged by the AMC Actor microcontroller modules used during runtime and saves it as multiple
    .feather files.

    Args:
        log_path: The path to the .npz archive containing the Actor AMC data to parse.
        output_directory: The path to the directory where to save the extracted data as .feather files.
        hardware_state: A HardwareState instance representing the state of the acquisition system that generated the
            data.
    """

def _process_sensor_data(log_path: Path, output_directory: Path, hardware_state: MesoscopeHardwareState) -> None:
    """Extracts the data logged by the AMC Sensor microcontroller modules used during runtime and saves it as multiple
    .feather files.

    Args:
        log_path: The path to the .npz archive containing the Sensor AMC data to parse.
        output_directory: The path to the directory where to save the extracted data as .feather files.
        hardware_state: A HardwareState instance representing the state of the acquisition system that generated the
            data.
    """

def _process_encoder_data(log_path: Path, output_directory: Path, hardware_state: MesoscopeHardwareState) -> None:
    """Extracts the data logged by the AMC Encoder microcontroller modules used during runtime and saves it as
    multiple .feather files.

    Notes:
        Currently, Encoder only records data from a single 'EncoderModule'.

    Args:
        log_path: The path to the .npz archive containing the Encoder AMC data to parse.
        output_directory: The path to the directory where to save the extracted data as .feather files.
        hardware_state: A HardwareState instance representing the state of the acquisition system that generated the
            data.
    """

def extract_log_data(session_data: SessionData, parallel_workers: int = 7, update_manifest: bool = False) -> None:
    """Reads the compressed .npz log files stored in the raw_data directory of the target session and extracts all
    relevant behavior data stored in these files into the processed_data directory.

    This function is intended to run on the BioHPC server as part of the 'general' data processing pipeline. It is
    optimized to process all log files in parallel and extract the data stored inside the files into the behavior_data
    directory and camera_frames directory.

    Args:
        session_data: The SessionData instance for the processed session.
        parallel_workers: The number of CPU cores (workers) to use for processing the data in parallel. Note, this
            number should not exceed the number of available log files.
        update_manifest: Determines whether to update (regenerate) the project manifest file for the processed
            session's project. This should always be enabled when working with remote compute server(s) to ensure that
            the project manifest file contains the most actual snapshot of the project's state.
    """
