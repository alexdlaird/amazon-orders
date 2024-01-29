import os

import responses
from click.testing import CliRunner

from amazonorders.cli import amazon_orders_cli
from amazonorders.constants import ORDER_DETAILS_URL
from tests.unittestcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "1.0.7"


class TestCli(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @responses.activate
    def test_history_command(self):
        # GIVEN
        year = 2023
        start_index = 10
        self.given_login_responses_success()
        resp1 = self.given_order_history_landing_exists()
        resp2 = self.given_order_history_exists(year, start_index)

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--username", "some-username", "--password",
                                       "some-password", "history", "--year",
                                       year, "--start-index", start_index])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp1.call_count)
        self.assertEqual(1, resp2.call_count)
        self.assertIn("Order #112-0069846-3887437", response.output)
        self.assertIn("Order #113-1909885-6198667", response.output)
        self.assertIn("Order #112-4188066-0547448", response.output)
        self.assertIn("Order #112-9685975-5907428", response.output)
        self.assertIn("Order #112-1544475-9165068", response.output)
        self.assertIn("Order #112-9858173-0430628", response.output)
        self.assertIn("Order #112-3899501-4971443", response.output)
        self.assertIn("Order #112-2545298-6805068", response.output)
        self.assertIn("Order #113-4970960-6452217", response.output)
        self.assertIn("Order #112-9733602-9062669", response.output)

    @responses.activate
    def test_order_command(self):
        # GIVEN
        order_id = "112-2961628-4757846"
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "order-details-112-2961628-4757846.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                "{}?orderID={}".format(ORDER_DETAILS_URL,
                                       order_id),
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--username", "some-username", "--password",
                                       "some-password", "order", order_id])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertIn("Order #112-2961628-4757846", response.output)
