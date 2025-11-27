"""A Python library that provides tools for processing non-visual behavior data acquired in the Sun (NeuroAI) lab.

See https://github.com/Sun-Lab-NBB/sl-behavior for more details.
API documentation: https://sl-behavior-api-docs.netlify.app/
Authors: Ivan Kondratyev, Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

# Ensures that console output is enabled
if not console.enabled:
    console.enable()
