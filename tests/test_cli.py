import unittest

from click.testing import CliRunner

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.2"


class TestCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_cli(self):
        pass
        # WHEN
        # self.runner.invoke(amazon_orders)
