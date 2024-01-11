import unittest

from amazonorders.cli import get_order_history
from click.testing import CliRunner

from tests.testcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class TestCli(UnitTestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(get_order_history,
                                      ["--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @unittest.skip("This test needs to be mocked against the resource files to work")
    def test_get_orders(self):
        # WHEN
        response = self.runner.invoke(get_order_history,
                                      ["--username", "some-user", "--password",
                                       "some-password"])

        # THEN
        # TODO: build this test out more
        self.assertEqual(0, response.exit_code)
        self.assertTrue(response.output.startswith("Order #"))
