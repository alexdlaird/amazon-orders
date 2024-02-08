import os

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.10"

VERSION = __version__

DEFAULT_COOKIE_JAR_PATH = os.path.join(os.path.expanduser("~"), ".config",
                                       "amazon-orders", "cookies.json")
DEFAULT_OUTPUT_DIR = os.getcwd()
