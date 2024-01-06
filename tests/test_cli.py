import unittest

from click.testing import CliRunner

from amazonorders.cli import amazon_orders

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Alex Laird"
__version__ = "0.0.1"


class TestCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_cli(self):
        # WHEN
        self.runner.invoke(amazon_orders)
