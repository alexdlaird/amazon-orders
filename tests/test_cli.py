import os

import responses

from amazonorders.cli import amazon_orders
from click.testing import CliRunner

from amazonorders.session import BASE_URL
from tests.testcase import UnitTestCase

__author__ = "Alex Laird"
__copyright__ = "Copyright 2024, Alex Laird"
__version__ = "0.0.3"


class TestCli(UnitTestCase):
    def setUp(self):
        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(amazon_orders,
                                      ["--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @responses.activate
    def test_history_command(self):
        # GIVEN
        year = 2023
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "orders.html"), "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )
            responses.add(
                responses.GET,
                "{}/your-orders/orders?timeFilter=year-{}".format(BASE_URL,
                                                                  year),
                body=orders_page,
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders,
                                      ["--username", "some-user", "--password",
                                       "some-password", "history", "--year",
                                       year])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual("""Order #123-4567890-1234563: "[<Item: "The Simpsons - The Complete Fourth Season [DVD] (2004)">]"
Order #123-4567890-1234562: "[<Item: "The Simpsons - The Complete Fifth Season [DVD] (2004) Doris Grau; Marcia...">]"
Order #123-4567890-1234561: "[<Item: "The Emperor's New Groove [DVD] (2001) David Spade; John Goodman; Eartha Kitt...">]"
""", response.output)

    @responses.activate
    def test_order_command(self):
        # GIVEN
        order_id = "123-4567890-1234563"
        with open(os.path.join(self.RESOURCES_DIR, "signin.html"), "r") as f:
            responses.add(
                responses.GET,
                "{}/gp/sign-in.html".format(BASE_URL),
                body=f.read(),
                status=200,
            )
        with open(os.path.join(self.RESOURCES_DIR, "order-details.html"),
                  "r") as f:
            orders_page = f.read()
            responses.add(
                responses.POST,
                "{}/ap/signin".format(BASE_URL),
                body=orders_page,
                status=200,
            )
            responses.add(
                responses.GET,
                "{}/gp/your-account/order-details?orderID={}".format(BASE_URL,
                                                                     order_id),
                body=orders_page,
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders,
                                      ["--username", "some-user", "--password",
                                       "some-password", "order", order_id])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(
            'Order #123-4567890-1234563: "[<Item: "The Simpsons - The Complete Fourth Season [DVD] (2004)">]"\n',
            response.output)
