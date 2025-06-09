__copyright__ = "Copyright (c) 2024-2025 Alex Laird"
__license__ = "MIT"

import datetime
import os
from unittest.mock import Mock, patch

import responses
from click.testing import CliRunner

from amazonorders.cli import amazon_orders_cli
from tests.unittestcase import UnitTestCase


class TestCli(UnitTestCase):
    def setUp(self):
        super().setUp()

        self.runner = CliRunner()

    def test_missing_credentials(self):
        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "--username", "", "--password", ""])

        # THEN
        self.assertEqual(2, response.exit_code)
        self.assertTrue("Usage: " in response.output)

    @responses.activate
    def test_history_command(self):
        # GIVEN
        year = 2023
        start_index = 10
        self.given_login_responses_success()
        resp = self.given_order_history_exists(year, start_index)

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "--username", "some-username", "--password",
                                       "some-password", "history", "--year",
                                       year, "--start-index", start_index, "--single-page"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assert_login_responses_success()
        self.assertEqual(1, resp.call_count)
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
        with open(os.path.join(self.RESOURCES_DIR, "orders", "order-details-112-2961628-4757846.html"), "r",
                  encoding="utf-8") as f:
            resp1 = responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "--username", "some-username", "--password",
                                       "some-password", "order", order_id])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp1.call_count)
        self.assertIn("Order #112-2961628-4757846", response.output)

    @responses.activate
    @patch("amazonorders.transactions.datetime", wraps=datetime)
    def test_transactions_command(self, mock_get_today: Mock):
        # GIVEN
        mock_get_today.date.today.return_value = datetime.date(2024, 10, 11)
        days = 1
        self.given_login_responses_success()
        with open(os.path.join(self.RESOURCES_DIR, "transactions", "get-transactions-snippet.html"),
                  "r", encoding="utf-8") as f:
            resp = responses.add(
                responses.POST,
                f"{self.test_config.constants.TRANSACTION_HISTORY_URL}",
                body=f.read(),
                status=200,
            )

        # WHEN
        response = self.runner.invoke(
            amazon_orders_cli,
            [
                "--config-path",
                self.test_config.config_path,
                "--username",
                "some-username",
                "--password",
                "some-password",
                "transactions",
                "--days",
                days,
            ],
        )

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertEqual(1, resp.call_count)
        self.assertIn("1 transactions parsed", response.output)
        self.assertIn("Transaction: 2024-10-11\n  Order #123-4567890-1234567\n  Grand Total: -$45.19", response.output)

    def test_update_config(self):
        # GIVEN
        self.test_config.save()
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("max_auth_attempts: 10", f.read())

        # WHEN
        response = self.runner.invoke(amazon_orders_cli,
                                      ["--config-path", self.test_config.config_path,
                                       "update-config", "max_auth_attempts", "7"])

        # THEN
        self.assertEqual(0, response.exit_code)
        self.assertIn("max_auth_attempts\" updated", response.output)
        with open(self.test_config.config_path, "r") as f:
            self.assertIn("max_auth_attempts: 7", f.read())

    @responses.activate
    def test_invoice_command(self):
        # GIVEN
        order_id = "112-2961628-4757846"
        self.given_login_responses_success()
        responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_INVOICE_URL}?orderID={order_id}",
            body=b"PDFDATA",
            status=200,
            content_type="application/pdf",
        )

        # WHEN
        with self.runner.isolated_filesystem():
            output_file = "invoice.pdf"
            response = self.runner.invoke(
                amazon_orders_cli,
                [
                    "--config-path",
                    self.test_config.config_path,
                    "--username",
                    "some-username",
                    "--password",
                    "some-password",
                    "invoice",
                    order_id,
                    "--output-file",
                    output_file,
                ],
            )

            # THEN
            self.assertEqual(0, response.exit_code)
            self.assertTrue(os.path.exists(output_file))

    @responses.activate
    def test_history_command_download_invoices(self):
        # GIVEN
        year = 2024
        order_id = "112-5939971-8962610"
        self.given_login_responses_success()
        self.given_order_history_exists(year)
        with open(
            os.path.join(self.RESOURCES_DIR, "orders", f"order-details-{order_id}.html"),
            "r",
            encoding="utf-8",
        ) as f:
            responses.add(
                responses.GET,
                f"{self.test_config.constants.ORDER_DETAILS_URL}?orderID={order_id}",
                body=f.read(),
                status=200,
            )
        responses.add(
            responses.GET,
            f"{self.test_config.constants.ORDER_INVOICE_URL}?orderID={order_id}",
            body=b"PDFDATA",
            status=200,
            content_type="application/pdf",
        )

        # WHEN
        with self.runner.isolated_filesystem():
            response = self.runner.invoke(
                amazon_orders_cli,
                [
                    "--config-path",
                    self.test_config.config_path,
                    "--username",
                    "some-username",
                    "--password",
                    "some-password",
                    "--output-dir",
                    ".",
                    "history",
                    "--year",
                    year,
                    "--single-page",
                    "--full-details",
                    "--invoices",
                ],
            )

            # THEN
            self.assertEqual(0, response.exit_code)
            self.assertTrue(os.path.exists(f"{order_id}.pdf"))
