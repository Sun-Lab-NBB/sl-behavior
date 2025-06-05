"""A Python library that provides tools for processing non-visual behavior data acquired in the Sun (NeuroAI) lab.

See https://github.com/Sun-Lab-NBB/sl-behavior for more details.
API documentation: https://sl-behavior-api-docs.netlify.app/
Authors: Ivan Kondratyev, Kushaan Gupta, Natalie Yeung
"""

from .legacy import extract_gimbl_data
from .log_processing import extract_log_data

__all__ = ["extract_gimbl_data", "extract_log_data"]
