from enum import IntEnum
from typing import TypedDict
from pathlib import Path
from collections.abc import Callable as Callable

import numpy as np
from numpy.typing import NDArray as NDArray
from sl_shared_assets import MesoscopeHardwareState
from ataraxis_communication_interface import ExtractedModuleData as ExtractedModuleData

from .utilities import interpolate_data as interpolate_data

class MicrocontrollerLogIds(IntEnum):
    ACTOR = 101
    SENSOR = 152
    ENCODER = 203

class _ParseTask(TypedDict):
    func: Callable[..., None]
    output: Path
    kwargs: dict[str, bool | np.float64 | np.uint16 | int]

def _parse_encoder_data(
    extracted_module_data: ExtractedModuleData, output_file: Path, cm_per_pulse: np.float64
) -> None: ...
def _parse_ttl_data(extracted_module_data: ExtractedModuleData, output_file: Path) -> None: ...
def _parse_brake_data(
    extracted_module_data: ExtractedModuleData,
    output_file: Path,
    maximum_brake_strength: np.float64,
    minimum_brake_strength: np.float64,
) -> None: ...
def _parse_valve_data(
    extracted_module_data: ExtractedModuleData,
    output_file: Path,
    scale_coefficient: np.float64,
    nonlinearity_exponent: np.float64,
) -> None: ...
def _parse_gas_puff_data(extracted_module_data: ExtractedModuleData, output_file: Path) -> None: ...
def _parse_lick_data(
    extracted_module_data: ExtractedModuleData, output_file: Path, lick_threshold: np.uint16
) -> None: ...
def _parse_torque_data(
    extracted_module_data: ExtractedModuleData, output_file: Path, torque_per_adc_unit: np.float64
) -> None: ...
def _parse_screen_data(
    extracted_module_data: ExtractedModuleData, output_file: Path, *, initially_on: bool
) -> None: ...
def _parse_module_data(
    parse_func: Callable[..., None],
    extracted_data: ExtractedModuleData | None,
    output_file: Path,
    **kwargs: bool | np.float64 | np.uint16 | int,
) -> Exception | None: ...
def _extract_mesoscope_vr_actor_data(
    log_path: Path, output_directory: Path, hardware_state: MesoscopeHardwareState, workers: int
) -> None: ...
def _extract_mesoscope_vr_sensor_data(
    log_path: Path, output_directory: Path, hardware_state: MesoscopeHardwareState, workers: int
) -> None: ...
def _extract_mesoscope_vr_encoder_data(
    log_path: Path, output_directory: Path, hardware_state: MesoscopeHardwareState, workers: int
) -> None: ...
def process_microcontroller_data(session_path: Path, log_id: int, workers: int = -1) -> None: ...
