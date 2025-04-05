from dataclasses import dataclass
from ataraxis_data_structures import YamlConfig


@dataclass()
class HardwareConfiguration(YamlConfig):
    """This class is used to save the runtime hardware configuration parameters as a .yaml file.

    This information is used to read and decode the data saved to the .npz log files during runtime as part of data
    processing.

    Notes:
        All fields in this dataclass initialize to None. During log processing, any log associated with a hardware
        module that provides the data stored in a field will be processed, unless that field is None. Therefore, setting
        any field in this dataclass to None also functions as a flag for whether to parse the log associated with the
        module that provides this field's information.

        This class is automatically configured by MesoscopeExperiment and BehaviorTraining classes to facilitate log
        parsing.
    """

    cue_map: dict[int, float] | None = None
    """MesoscopeExperiment instance property."""
    cm_per_pulse: float | None = None
    """EncoderInterface instance property."""
    maximum_break_strength: float | None = None
    """BreakInterface instance property."""
    minimum_break_strength: float | None = None
    """BreakInterface instance property."""
    lick_threshold: int | None = None
    """BreakInterface instance property."""
    valve_scale_coefficient: float | None = None
    """ValveInterface instance property."""
    valve_nonlinearity_exponent: float | None = None
    """ValveInterface instance property."""
    torque_per_adc_unit: float | None = None
    """TorqueInterface instance property."""
    screens_initially_on: bool | None = None
    """ScreenInterface instance property."""
    recorded_mesoscope_ttl: bool | None = None
    """TTLInterface instance property."""
