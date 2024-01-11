import os
import unittest

from amazonorders.cli import get_order_history
from click.testing import CliRunner

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class TestCli(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(get_order_history, ["--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @unittest.skipIf(not (os.environ.get("AMAZON_USERNAME") and os.environ.get("AMAZON_PASSWORD")), "AMAZON_USERNAME and AMAZON_PASSWORD environment variables not set")
    def test_get_orders(self):
        # WHEN
        response = self.runner.invoke(get_order_history)

        # THEN
        # TODO: build this test out more
        self.assertEqual(0, response.exit_code)
        self.assertTrue(response.output.startswith("Order #"))
