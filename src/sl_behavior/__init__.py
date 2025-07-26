"""A Python library that provides tools for processing non-visual behavior data acquired in the Sun (NeuroAI) lab.

See https://github.com/Sun-Lab-NBB/sl-behavior for more details.
API documentation: https://sl-behavior-api-docs.netlify.app/
Authors: Ivan Kondratyev, Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .legacy import extract_gimbl_data
from .log_processing import extract_log_data

# Ensures that console output is enabled
if not console.enabled:
    console.enable()

__all__ = ["extract_gimbl_data", "extract_log_data"]
