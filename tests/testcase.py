import os
import unittest

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


@unittest.skipIf(os.environ.get("INTEGRATION_TESTS", "False") == "True",
                 "Skipping, INTEGRATION_TESTS=True was set in the environment")
class UnitTestCase(unittest.TestCase):
    pass
