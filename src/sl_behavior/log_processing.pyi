from typing import Any
from pathlib import Path

import numpy as np
from _typeshed import Incomplete
from numpy.typing import NDArray as NDArray
from sl_shared_assets import SessionData, MesoscopeHardwareState
from ataraxis_communication_interface import ExtractedModuleData

_supported_acquisition_systems: Incomplete

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

def _process_experiment_data(log_path: Path, output_directory: Path, cue_map: dict[int, float] | None = None) -> None:
    """Extracts the acquisition system states, experiment states, and any additional system-specific data from the log
    generated during an experiment runtime and saves the extracted data as Polars DataFrame .feather files.

    This extraction method functions similar to camera log extraction and hardware module log extraction methods. The
    key difference is that this function contains additional arguments, that allow specializing it for extracting the
    data generated by different acquisition systems used in the Sun lab.

    Args:
        log_path: The path to the .npz archive containing the VR and experiment data to parse.
        output_directory: The path to the directory where to save the extracted data as .feather files.
        cue_map: The dictionary mapping cue IDs to their corresponding distances in centimeters. This argument is only
            used when parsing the data acquired by the Mesoscope-VR data acquisition system.
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

def extract_log_data(session_data: SessionData, parallel_workers: int = 6) -> None:
    """Reads the compressed .npz log files stored in the raw_data directory of the target session and extracts all
    relevant behavior data stored in these files into the processed_data directory.

    This function is intended to run on the BioHPC server as part of the 'general' data processing pipeline. It is
    optimized to process all log files in parallel and extract the data stored inside the files into behavior_data
    directory and camera_frames directory.

    Args:
        session_data: The SessionData instance for the processed session.
        parallel_workers: The number of CPU cores (workers) to use for processing the data in parallel. Note, this
            number should not exceed the number of available log files.
    """
