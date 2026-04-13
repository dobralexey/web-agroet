"""Top-level package for geeet."""

__author__ = """Oliver Lopez"""
__email__ = 'lopezv.oliver@gmail.com'
__version__ = '0.3.0'

import src.web_agroet.geeet.ptjpl
import src.web_agroet.geeet.tseb

# Optional gee features (requires earthengine-api to be installed)
try:
    import geeet.eepredefined
except ImportError:
    pass